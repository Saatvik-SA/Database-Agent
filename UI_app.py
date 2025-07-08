# UI_app.py

import os
import streamlit as st
import sqlite3
from dotenv import load_dotenv
from PIL import Image

from DB_loader import connect_to_sqlite, load_excel_as_sqlite
from SQL_agent import create_agent, run_query

load_dotenv()

# --- Load database ---
DATA_SOURCE = "Data/olist.sqlite"  # Change to .xlsx path if needed
print("ABSOLUTE PATH:", os.path.abspath(DATA_SOURCE))
print("File exists:", os.path.exists(DATA_SOURCE))


conn = connect_to_sqlite(DATA_SOURCE)
cursor = conn.cursor()
agent = create_agent(DATA_SOURCE)

# --- Load CSS ---
def load_css(path):
    with open(path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("Static/styles.css")

# --- Display Logo & Title ---
st.image("Static/EY-logo.png", width=300)
st.title("Structured Database LLM Agent")
st.subheader("Natural Language Q&A with Google Gemini AI")

# --- Display Chat Bubbles ---
def chat_bubble(origin, message):
    bubble_type = "ai-bubble" if origin == "ai" else "human-bubble"
    reverse_class = "row-reverse" if origin == "human" else ""
    return f"""
    <div class="chat-row {reverse_class}">
        <div class="chat-bubble {bubble_type}">
            &#8203;{message}
        </div>
    </div>
    """

# --- Session State ---
if "history" not in st.session_state:
    st.session_state.history = []

# --- Helper to get schema info ---
def get_and_display_table_info(cursor, tables):
    info = ""
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        info += f"Table: {table}\n"
        for column in columns:
            info += f"    {column[1]} ({column[2]})\n"
        info += "\n"
    return info

# --- Build Your Custom Prefix ---
prefix = f'''
You are an agent designed to interact with a SQL database.
Your job is when given an input question, schema and sample rows to create a syntactically correct query for the data.

You are an expert data analysis assistant. As an expert, you must iterate through multiple tables of the dataset and respond in clear, natural language when given a query about the data. Here are some examples to guide your responses:
Example 1:
User Query: "Show me the columns in the dataset."
Your Response: "The columns in the dataset include: 'order_id', 'customer_id', 'order_status', 'order_purchase_timestamp', 'order_delivered_customer_date', 'product_id', 'seller_id', 'price', 'freight_value', 'payment_type', 'review_score', and many others."

Example 2:
User Query: "What is the average price of products?"
Your Response: "The average price of products in the dataset is BRL 150.00."

Example 3:
User Query: "Provide a summary of the dataset."
Your Response: "The dataset contains 11 tables: customers, geolocation, leads_closed, leads_qualified, order_items, order_payments, order_reviews, orders, product_category_name_translation, products, and sellers. The dataset includes over 100,000 orders. The average product price is BRL 150.00. The most common payment method is 'credit card'. The average review score is 4.0."

The data you are querying is related to e-commerce orders and data is captured at transaction level. 
The hierarchy of columns from highest level to lowest level is as follows: ORDER_ID, CUSTOMER_ID, PRODUCT_ID, SELLER_ID.

Schema of tables and sample rows:

{get_and_display_table_info(cursor, ['orders', 'customers', 'products', 'sellers'])}

Please follow these guidelines when generating SQL queries:
- Always use MSSQL syntax for your queries.
- Do not use any DML (Data Manipulation Language) statements such as INSERT, UPDATE, DELETE, or DROP.
- When growth, comparison related questions are asked along with numbers calculate percentage as well.
- Limit the number of retrieved rows to a maximum of 100.
- Verify the correctness of your query.
- When the question references specific columns or calculations, only include relevant columns.
- Maintain proper case sensitivity when filtering by 'Country Name' (e.g., 'Brazil' instead of 'brazil').
- In case of references to Customer_Name or Product_Name or Seller_Name, please consider whole data for calculation.
- If QoQ, YoY, MoM related questions are asked, please consider whole data for calculation.
- If no date information is mentioned in the question or question is generic consider whole data for calculation.

- Note this is not time series continuous data, it is transaction level data. As this is transaction level data, consider whole data for calculation.

To assist you, here are some sample examples of questions and SQL queries:

1. Question: What is the information for product ID 1e9e8ef04dbcff4541ed26657ea517e5 ?
   Answer: SELECT product_id,product_length_cm,product_height_cm,product_weight_g FROM products WHERE product_id = '1e9e8ef04dbcff4541ed26657ea517e5';

2. Question: How many orders were placed by customer ID 06b8999e2fba1a1fbc88172c00ba8bc7 in the last month?
   Answer: SELECT COUNT(order_id) FROM orders WHERE customer_id = 06b8999e2fba1a1fbc88172c00ba8bc7 AND order_date >= DATEADD(month, -1, GETDATE());

3. Question: What is the average delivery time for orders in the last quarter?
   Answer: SELECT AVG(DATEDIFF(day, order_date, delivery_date)) FROM orders WHERE order_date >= DATEADD(quarter, -1, GETDATE());

4. Question: Which products have the highest return rates?
   Answer: SELECT product_id, (COUNT(CASE WHEN return_flag = 'Y' THEN 1 END) / COUNT(*)) AS return_rate FROM orders GROUP BY product_id ORDER BY return_rate DESC;

5. Question: What is the number of orders delivered between 7th june 2017 and 5th september 2017?
   Answer: SELECT COUNT(*) AS order_status = delivered FROM orders WHERE order_delivered_customer_date BETWEEN '2017-06-07' AND '2017-09-05';

6. Question: What is the total revenue generated from orders in the year 2017?
   Answer: SELECT SUM(price) AS total_revenue FROM order_items WHERE shipping_limit_date BETWEEN '2017-01-01' AND '2017-12-31';

INSTRUCTIONS:
- If the question does not seem related to the database, simply return "I don't know."
- If no time period is mentioned in the question, automatically filter by latest month and latest year.
- If multiple year and months are mentioned in the question, include month and year in the select statements as well.
- Understand abbreviations as follows, YoY = Year over Year, MoM = Month over Month, QoQ = Quarter Over Quarter.
- (IMPORTANT) Only the SQL Query should be the answer, nothing in front, nothing after it.
'''


# --- UI setup ---
chat_container = st.container()
input_form = st.form("chat-form")

# --- Display chat history ---
with chat_container:
    for chat in st.session_state.history:
        st.markdown(chat_bubble(chat["origin"], chat["message"]), unsafe_allow_html=True)

# --- Input form ---
with input_form:
    cols = st.columns((6, 1))
    user_input = cols[0].text_input(
        "Ask your question",
        placeholder="e.g. What’s the average delivery time?",
        label_visibility="collapsed",
        key="user_input"
    )
    submitted = cols[1].form_submit_button("Ask")

if submitted and user_input:
    st.session_state.history.append({"origin": "human", "message": user_input})

    try:
        full_query = prefix + user_input
        response = run_query(agent, full_query)
    except Exception as e:
        response = f"Error: {str(e)}"

    st.session_state.history.append({"origin": "ai", "message": response})

    del st.session_state["user_input"]
    st.rerun()



