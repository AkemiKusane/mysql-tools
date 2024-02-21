import io
import re
import sys

class TableInfo:
    def __init__(self, join_type, table_name):
        self.join_type = join_type
        self.table_name = table_name
class QueryNode:
    def __init__(self, query_text):
        self.query_text = query_text
        self.subqueries = [] # 子查询
        self.query_type = self.determine_query_type()
        self.tables_list = []
        if self.query_type.lower() in ["select","delete","update","insert"]:
            self.tables_list = self.find_table_in_queries(query_text)

    def add_subquery(self, subquery):
        self.subqueries.append(subquery)

    def determine_query_type(self):
        # 确定查询类型
        first_word = self.query_text.split()[0]
        return first_word

    def find_table_in_queries(self, query):
        # 定义状态
        SEARCHING_KEYWORD, READING_TABLE_NAME, SKIPPING_ALIAS, DONE = range(4)
        state = SEARCHING_KEYWORD
        table_infos = []

        words = query.split()
        i = 0
        query_type = words[0].upper()  # 初始查询类型为整个查询的第一个单词

        while i < len(words) and state != DONE:
            word = words[i].lower()

            if state == SEARCHING_KEYWORD:
                if word in ["insert", "delete", "update", "from", "into"]:
                    state = READING_TABLE_NAME
                elif word == "select": # 针对INSERT-SELECT
                    query_type = 'SELECT'
                elif word == 'join':
                    join_type = 'INNER'  # 默认为INNER JOIN
                    prev_word = words[i-1].lower() if i > 0 else ''
                    if prev_word in ['left', 'right']:
                        join_type = 'OUTER'
                    elif prev_word == 'cross':
                        join_type = 'OTHER'
                    query_type = join_type + " JOIN"
                    if words[i+1].lower() == 'outer':
                        i += 1  # 跳过OUTER关键字
                    state = READING_TABLE_NAME
                    
            elif state == READING_TABLE_NAME:
                if word[0] == '(':
                    # 遇到子查询/values, 跳过子查询/values
                    while i < len(words) and words[i] != ')':
                        i += 1
                    state = SEARCHING_KEYWORD # 回到寻找关键字
                elif word in ["as", "values", "into", "from"]:
                    state = SKIPPING_ALIAS
                else:
                    table_name = word.replace(',', '')  # 移除可能的逗号和分号
                    table_infos.append(TableInfo(query_type, table_name)) # 首先这个是表名
                    while word.endswith(',') or words[i+1].startswith(','): # 如果该单词最后一个字符为逗号, 或者下一个字符的开始为逗号, 则存在多个同类型的表名
                        i += 1
                        word = words[i].lower()
                        table_infos.append(TableInfo(query_type, word.replace(',', ''))) # 把这个词也加进去                       
                    if word.endswith(';'):
                        state = DONE  # 如果这之后是分号，结束解析
                    state = SEARCHING_KEYWORD # 回到寻找关键字

            if state == SKIPPING_ALIAS:
                state = READING_TABLE_NAME  # 继续寻找下一个可能的表名或结束

            i += 1

        return table_infos


def preprocess_file_content(filepath):
    """预处理文件内容：替换多个连续空格和换行符为单个空格。"""
    with io.open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
        content = re.sub(r'\s+', ' ', content)  # 将所有空白字符替换为单个空格
    return content

def get_sql_queries(content):
    """提取SQL查询，包括declare语句。"""
    start_keywords = ['create', 'select', 'insert', 'update', 'delete', 'truncate', 'drop', 'declare']
    queries = []
    words = content.split(' ')
    current_query = []
    is_query = False

    for word in words:
        # 检查是否是起始关键字，开始一个新的查询
        if not is_query and any(word.lower().startswith(keyword) for keyword in start_keywords):
            is_query = True
            current_query = [word]  # 开始收集新的查询
        elif is_query:
            # 如果已经在收集一个查询，继续收集
            current_query.append(word)
            # 如果当前单词以分号结束，表示当前查询结束
            if word.endswith(';'):
                queries.append(' '.join(current_query))
                is_query = False
                current_query = []

    # 确保收集最后一个查询，如果它没有以分号结尾
    if current_query:
        queries.append(' '.join(current_query))

    return queries

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get_tables.py <filepath>")
        sys.exit(1)

    filepath = sys.argv[1]
    content = preprocess_file_content(filepath)
    queries = get_sql_queries(content)
    querynodes = []

    output_file_path = 'output.txt'
    with io.open(output_file_path, 'w', encoding='utf-8') as file:
        for query in queries:
            querynode = QueryNode(query)
            file.write(querynode.query_text + u'\n')
            for table in querynode.tables_list:
                file.write(str(table.join_type) + ' '+ str(table.table_name) + u'\n')
            

    print("Queries have been written to:", output_file_path)
