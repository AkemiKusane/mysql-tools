#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <database_name> <procedure_name>"
    exit 1
fi

# MySQL connection parameters
cnf_file="/path/to/your/cnf/file"
database=$1
procedure=$2

# Function to extract and process the table name and JOIN statement from a SELECT or UPDATE statement
process_select_or_update() {
    local statement=$1

    # Extract the table name
    local table_name=$(echo "$statement" | grep -oiP '(FROM|UPDATE) \K[a-zA-Z0-9._]+')

    # Check if there is a JOIN clause
    if [[ $statement =~ JOIN ]]; then
        # Extract the JOIN clause
        local join_clause=$(echo "$statement" | grep -oiP 'JOIN [a-zA-Z0-9._]+[^WHERE|ORDER|SET]*')
        # Add the JOIN clause to the SELECT statement
        select_statement="SELECT * FROM $table_name $join_clause LIMIT 0"
    else
        select_statement="SELECT * FROM $table_name LIMIT 0"
    fi

    # Execute the SELECT statement and measure the execution time using MySQL's profiling
    echo "Profiling $select_statement..."
    mysql --defaults-extra-file=$cnf_file -D$database -e "SET profiling = 1; $select_statement; SHOW PROFILES; SET profiling = 0;"
}

# Function to extract and save the table name from an INSERT statement
process_insert() {
    local statement=$1

    # Extract the table name
    local table_name=$(echo "$statement" | grep -oiP 'INTO \K[a-zA-Z0-9._]+')
    echo "Found INSERT statement for table $table_name"
}

# Connect to the MySQL server and get the procedure's body
procedure_body=$(mysql --defaults-extra-file=$cnf_file -D$database -Bse "SELECT ROUTINE_DEFINITION FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_SCHEMA='$database' AND ROUTINE_NAME='$procedure'")

# Find all SELECT, UPDATE and INSERT statements
sql_statements=$(echo "$procedure_body" | grep -oiP '(SELECT[^;]*FROM [a-zA-Z0-9._]+[^;]*|UPDATE [a-zA-Z0-9._]+ SET [^;]*|INSERT INTO [a-zA-Z0-9._]+ VALUES [^;]*)')

# Process each SQL statement
for sql_statement in $sql_statements; do
    if [[ $sql_statement =~ ^SELECT ]]; then
        process_select_or_update "$sql_statement"
    elif [[ $sql_statement =~ ^UPDATE ]]; then
        process_select_or_update "$sql_statement"
    elif [[ $sql_statement =~ ^INSERT ]]; then
        process_insert "$sql_statement"
    fi
done
