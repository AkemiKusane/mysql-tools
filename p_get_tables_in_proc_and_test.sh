#!/bin/bash

database=$1
stored_procedure=$2
cnf_file=$3

procedure_body=$(mysql --defaults-extra-file=$cnf_file -D$database -e "SHOW CREATE PROCEDURE $stored_procedure\G" | grep -oiP 'CREATE DEFINER.*BEGIN\s*\K.*(?=END)')

statements=$(echo "$procedure_body" | grep -oiP '(SELECT[^;]*FROM `[^;]*`)|(UPDATE `[^;]*`)|(INSERT INTO `[^;]*`)')

while IFS= read -r statement; do
    if [[ $statement =~ ^INSERT ]]; then
        # This is an INSERT statement, extract the table name and store it
        table_name=$(echo "$statement" | grep -oiP 'INSERT INTO \K[a-zA-Z0-9._]+')
        echo "Found INSERT statement on table: $table_name"
    elif [[ $statement =~ ^SELECT || $statement =~ ^UPDATE ]]; then
        # This is a SELECT or UPDATE statement, process it
        process_select_or_update "$statement"
    fi
done <<< "$statements"

process_select_or_update() {
    local statement=$1

    # Extract the table name
    local table_name=$(echo "$statement" | grep -oiP '(FROM|UPDATE) \K[a-zA-Z0-9._]+')

    # Check if there is a JOIN clause
    if [[ $statement =~ JOIN ]]; then
        # Extract the JOIN clause
        local join_clause=$(echo "$statement" | grep -oiP 'JOIN [a-zA-Z0-9._]+[^WHERE|ORDER|SET]*')
        # Add the JOIN clause to the SELECT statement
        select_statement="SELECT SQL_NO_CACHE * FROM $table_name $join_clause LIMIT 1000;"
    else
        select_statement="SELECT SQL_NO_CACHE * FROM $table_name LIMIT 1000;"
    fi

    # Execute the SELECT statement and measure the execution time using MySQL's profiling
    echo "Profiling $select_statement..."
    mysql --defaults-extra-file=$cnf_file -D$database -e "SET profiling = 1; pager cat > /dev/null; $select_statement; nopager; SHOW PROFILES; SET profiling = 0;"
}
