
# %%
import streamlit as st
import pyperclip

import requests
from bs4 import BeautifulSoup

import pandas as pd
import io

# Functions
def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        st.success("Copied to clipboard!")
    except pyperclip.PyperclipException as e:
        st.warning("Clipboard functionality currently not supported. Copy the link address below...")
        st.markdown(f"[Website]({text})", unsafe_allow_html=True)

def clean_numeric_columns(df, col_names):
    """
    Cleans the specified columns in the DataFrame by removing non-numeric characters
    and converting them to numeric.
    
    Parameters:
    df (pd.DataFrame): The DataFrame to process.
    col_names (list): A list of column names to clean.
    
    Returns:
    pd.DataFrame: A DataFrame with the specified columns cleaned and converted to numeric.
    """
    cleaned_df = df.copy()  # Avoid modifying the original DataFrame
    
    for col in col_names:
        if col in cleaned_df.columns:  # Ensure column exists
            cleaned_df[col] = (
                cleaned_df[col]
                .astype(str)
                .str.replace(r"[^\d\.\-]", "", regex=True)  # Remove non-numeric characters except '.' and '-'
            )
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')  # Convert to numeric, coercing errors to NaN
    
    return cleaned_df

## Introduction
st.title("Wikipedia Table Scraper")
st.subheader("Introduction")
st.write("""
         This app is one of many options in the world to easily webscrape data for personal use. Wikipedia 
         is open source, and thus one of the most webscraped domains on the internt. However, webscraping can be difficult for those not
         familiar to it. Furthermore, copying and pasting raw data from a Wikipedia table onto an Excel workbook has plenty of formatting errors.
         The app's main purpose is to remove the difficulty of webscraping, with features that allow users to reframe the dimensions of the table,
         identify the numeric columns, and export it to a CSV or Excel file. 
         """)

# %%
## Step 1: Insert URL
st.subheader("Step 1: Select a Wikipedia Page")
url1 = 'https://en.wikipedia.org/wiki/Economy_of_the_United_States'
url2 = 'https://en.wikipedia.org/wiki/Crime_in_the_United_States'
url3 = 'https://en.wikipedia.org/wiki/List_of_highest-grossing_films'

url = st.text_input("Enter a wikipedia URL", key="url")

st.write("Examples")
if st.button("US Economics"):
    copy_to_clipboard(url1)

if st.button("US Crime Rates"):
    copy_to_clipboard(url2)

if st.button("Top Grossing Films"):
    copy_to_clipboard(url3)

if not url:
    st.warning("⚠️ Please paste in a Wikipedia page link to proceed.")
    st.stop()

# extract data (assumed to be class wikitable)
tbl_class = "wikitable"
page = requests.get(url)
soup = BeautifulSoup(page.content, "html.parser")
tables = soup.find_all("table", class_ = tbl_class)
table_count = f"Number of tables found: {len(tables)}"
if (len(tables) == 0):
    st.warning("⚠️ Wikipedia page has no objects of HTML class 'wikitable'. Consider using a different page")
    st.stop()
else:
    st.write(table_count)

# %%
## Step 2: Pick table of interest, turn into dataframe
st.subheader("Step 2: Select Table and Dimensions")
st.number_input("Enter which number table to extract", 1, len(tables), key = "idx")
idx = st.session_state.idx-1 # table number of interest
toi = tables[idx]

# %%
# Extract rows
rows = []
for tr in toi.find_all("tr"):
    cells = tr.find_all(["td", "th"]) 
    row = [cell.get_text(strip=True) for cell in cells]
    rows.append(row)

use_headers = st.checkbox("Do you want to use the column names found in the data?", value=True)
if use_headers:
    # User selects the row that contains headers
    which_header = st.number_input("Select the row header", 1, len(rows), key="which_header") - 1
    headers = rows[which_header]
    rows = rows[which_header+1:]

    # Validate that the header and rows have consistent lengths
    if not all(len(headers) == len(row) for row in rows):
        st.warning("⚠️ Table cannot render. Please change the row with the column names.")
        st.stop()  # Prevent further execution if the table is invalid
else: 
    # User specifies the first row of data
    which_first_row = st.number_input("Select the number that has the first row of data", 1, len(rows), key="which_first_row") - 1
    count_cols_needed = len(rows[which_first_row])

    # Prompt the user to enter custom column names
    ch_lbl = f"Enter {count_cols_needed} column names separated by commas:"
    custom_headers = st.text_input(ch_lbl, key="custom_headers")

    # Process custom column names
    if custom_headers:
        headers = [name.strip() for name in custom_headers.split(",")]
        if len(headers) != count_cols_needed:
            st.warning(f"⚠️ You entered {len(headers)} column names, but {count_cols_needed} are required.")
            st.stop()  # Prevent further execution if the column names don't match
    else:
        st.warning("⚠️ Please provide column names.")
        st.stop()
    
    rows = rows[which_first_row:]

# Get the columns to remove using multiselect
cols_to_remove = st.multiselect("Select the column names to remove", headers)

# Filter the DataFrame to keep only the selected columns
if cols_to_remove:
    df = pd.DataFrame(rows, columns=headers).drop(cols_to_remove, axis=1)  # Drop the specified columns
else:
    df = pd.DataFrame(rows, columns=headers)  # If no columns are selected, keep the whole DataFrame

df.columns = [f'{col}_{i}' if df.columns.tolist().count(col) > 1 else col for i, col in enumerate(df.columns)]
rows_to_keep = st.slider("Select the range of rows to keep", 1, len(df), (1, len(df)))
df = df.iloc[rows_to_keep[0]-1:rows_to_keep[1]]


# %%
## Step 3: Clean numeric columns
st.subheader("Step 3: Clean Numeric Columns")

# Select numeric columns
all_cols_num = st.checkbox("Are all columns numeric?", value=False)

if all_cols_num:
    selected_columns = list(df.columns)
else:
    selected_columns = st.multiselect("Select numeric columns", options=df.columns)

if selected_columns:
    r_err = st.number_input("Enter rounding error decimal places", min_value=0, value=0)
    thresh_err = st.number_input("Enter max number of digits", value = 16)
    df2 = clean_numeric_columns(df, col_names=selected_columns)
    numeric_cols = df2.select_dtypes(include=['number']).columns
    df2[numeric_cols] = df2[numeric_cols].round(r_err)

    # Apply check to identify and replace large integers with NaN
    for col in numeric_cols:
        df2[col] = df2[col].apply(lambda x: pd.NA if isinstance(x, (int, float)) and abs(x) > 10**thresh_err else x)

else: 
    df2 = df

## Step 4: Using the data editor
st.subheader("Step 4: Fix Remaining Cells")
st.write("Edit a value by double-clicking the cell") 
df3 = st.data_editor(df2)
st.write("Note: Some cells may require specific edits. Thousands-separator commas are native to Streamlit and do not affect final output.")

### Step 5: Download data file
st.subheader("Step 5: Download the Data")
userfilename = st.text_input("Enter in the desired name of your file", value="my_wikitable")

# CSV
@st.cache_data
def convert_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv = convert_csv(df3)

if st.download_button(
    label="Download data as CSV",
    data=csv,
    file_name=f'{userfilename}.csv',
    mime='text/csv',
):
    st.success("Downloaded CSV file successfully!")


# EXCEL
@st.cache_data
def convert_xlsx(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
    return output.getvalue()

xlsx = convert_xlsx(df3)

if st.download_button(
    label="Download data as Excel",
    data=xlsx,
    file_name=f'{userfilename}.xlsx',
    mime='application/vnd.ms-excel',
):
    st.success("Downloaded Excel file successfully!")
