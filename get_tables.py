import io
import re
import sys

class TableInfo:
    def __init__(self, join_type, table_name):
        self.join_type = join_type  # Type of join (e.g., INNER, OUTER, OTHER)
        self.table_name = table_name  # Name of the table involved in the join

class QueryNode:
    def __init__(self, query_text):
        self.query_text = query_text  # The SQL query text
        self.subqueries = []  # List to hold subqueries
        self.query_type = self.determine_query_type()  # Determine the type of the query (SELECT, DELETE, etc.)
        self.tables_list = []  # List to hold tables involved in the query
        if self.query_type.lower() in ["select", "delete", "update", "insert"]:
            self.tables_list = self.find_table_in_queries(query_text)  # Find tables in the query

    def add_subquery(self, subquery):
        self.subqueries.append(subquery)  # Add a subquery to the list of subqueries

    def determine_query_type(self):
        # Determine the type of the query based on the first word
        first_word = self.query_text.split()[0]
        return first_word

    def find_table_in_queries(self, query):
        # Define states for the state machine
        SEARCHING_KEYWORD, READING_TABLE_NAME, SKIPPING_ALIAS, DONE = range(4)
        state = SEARCHING_KEYWORD
        table_infos = []  # List to hold information about tables found in the query

        words = query.split()
        i = 0
        query_type = words[0].upper()  # Initial query type is the first word of the query

        while i < len(words) and state != DONE:
            word = words[i].lower()

            if state == SEARCHING_KEYWORD:
                if word in ["insert", "delete", "update", "from", "into"]:
                    state = READING_TABLE_NAME
                elif word == "select":  # For INSERT-SELECT cases
                    query_type = 'SELECT'
                elif word == 'join':
                    join_type = 'INNER'  # Default join type is INNER JOIN
                    prev_word = words[i-1].lower() if i > 0 else ''
                    if prev_word in ['left', 'right']:
                        join_type = 'OUTER'
                    elif prev_word == 'cross':
                        join_type = 'OTHER'
                    query_type = join_type + " JOIN"
                    if words[i+1].lower() == 'outer':
                        i += 1  # Skip the OUTER keyword
                    state = READING_TABLE_NAME
                    
            elif state == READING_TABLE_NAME:
                if word[0] == '(':
                    # Skip subqueries or values by jumping to the corresponding closing parenthesis
                    subquery = words[i].replace('(', '') + ' '
                    i += 1
                    while i < len(words) and not words[i].endswith(')'):
                        subquery += words[i] + " "
                        i += 1
                    if i < len(words):
                        subquery += words[i].replace(')', '')
                    self.subqueries.append(QueryNode(subquery))
                    state = SEARCHING_KEYWORD  # Return to searching for keywords
                elif word in ["as", "values", "into", "from"]:
                    state = SKIPPING_ALIAS
                else:
                    table_name = word.replace(',', '')  # Remove possible commas and semicolons
                    table_infos.append(TableInfo(query_type, table_name))  # Assume this word is a table name
                    # If the current word ends with a comma or the next character starts with a comma, there are multiple tables of the same type
                    while i<len(words)-1 and (word.endswith(',') or words[i+1].startswith(',')):
                        i += 1
                        word = words[i].lower()
                        table_infos.append(TableInfo(query_type, word.replace(',', '')))  # Add this word as well                       
                    if word.endswith(';'):
                        state = DONE  # If this is followed by a semicolon, end parsing
                    state = SEARCHING_KEYWORD  # Return to searching for keywords

            if state == SKIPPING_ALIAS:
                state = READING_TABLE_NAME  # Continue to look for the next possible table name or end

            i += 1

        return table_infos


def preprocess_file_content(filepath):
    """Preprocess file content: replace multiple consecutive spaces and newline characters with a single space."""
    with io.open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
        content = re.sub(r'\s+', ' ', content)  # Replace all whitespace characters with a single space
    return content

def get_sql_queries(content):
    """Extract SQL queries, including 'declare' statements."""
    start_keywords = ['create', 'select', 'insert', 'update', 'delete', 'truncate', 'drop', 'declare']
    queries = []
    words = content.split(' ')
    current_query = []
    is_query = False

    for word in words:
        # Check if it's a starting keyword to begin a new query
        if not is_query and any(word.lower().startswith(keyword) for keyword in start_keywords):
            is_query = True
            current_query = [word]  # Start collecting a new query
        elif is_query:
            # If already collecting a query, continue collecting
            current_query.append(word)
            # If the current word ends with a semicolon, it indicates the end of the current query
            if word.endswith(';'):
                queries.append(' '.join(current_query))
                is_query = False
                current_query = []

    # Make sure to collect the last query if it doesn't end with a semicolon
    if current_query:
        queries.append(' '.join(current_query))

    return queries

def collect_table_infos(query_node, collected_pairs):
    for table_info in query_node.tables_list:
        pair_str = "{} {}".format(table_info.join_type, table_info.table_name)
        collected_pairs.add(pair_str)
    
    for subquery in query_node.subqueries:
        collect_table_infos(subquery, collected_pairs)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python get_tables.py <filepath> <outputpath>")
        sys.exit(1)

    filepath = sys.argv[1]
    content = preprocess_file_content(filepath)
    queries = get_sql_queries(content)
    querynodes = []

    output_file_path = sys.argv[2]
    with io.open(output_file_path, 'w', encoding='utf-8') as file:
        table_group = set()
        for query in queries:
            querynode = QueryNode(query)
            file.write(querynode.query_text + u'\n')
            collect_table_infos(querynode, table_group)
        outputs = sorted(list(table_group))
        for output in outputs:
            file.write(f"{output}\n")


    print("Queries have been written to:", output_file_path)
