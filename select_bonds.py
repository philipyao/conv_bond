# 帮我用python写一段处理csv文件的程序，这个程序会根据csv文件中某些字段，按照一定规则来排序所有行。
# #说明：1. csv文件包含很多字段，取值可能是文本或者数字;
#   2. 规则配置在一个json文件中，配置项分为两类，第一类是排除类配置，排除某些字段等于、大于、小于特定值的行，第二类是排序配置，可以指定排序哪些字段，是正相关还是负相关，字段的权重值
#   3. 根据规则的配置，排除满足排除类的行
#   4. 根据规则的配置，为所有需要排序的字段排序，并记录其排序值（排名第1的记录为1），注意区分正相关还是负相关
#   5. 计算排序得分：得分 = 字段1排名*字段1权重 + 字段2排名*字段2权重 + ...，记录该排序得分
#   6. 根据排序得分，为剩余的行排序
#   7. 需要支持utf8编码的中文字符
#   8. 排除规则中增加字符串规则，如字符串类型的字段等于或包含特定字符串

# #要求：1. 打印排序后的所有行，包括所有原始字段及中间计算的排名、得分；
#    2. 打印排除的行，及其命中排除规则的字段

# 增加以下要求：1. 需要支持utf8编码的中文字符  2. 排除规则中增加字符串规则，如字符串类型的字段等于或包含特定字符串
# 排除规则中，再优化一下：== 的时候，值可能有多个，等于其中一个即可。

import csv
import json
from operator import itemgetter
import os

# 加载规则
with open('rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

data_file = rules['file']
exclusion_rules = rules['exclusion_rules']
sorting_rules = rules['sorting_rules']

data_dir = "data"
directory = "result"
if not os.path.exists(directory):
    os.makedirs(directory)
result_filename = f'result\{data_file.split(".")[0]}_result.csv'
simple_filename = f'result\{data_file.split(".")[0]}_simple.csv'
exclude_filename = f'result\{data_file.split(".")[0]}_exclude.csv'


# 文件预处理，去掉 bom头
import codecs
def convert_utf8_with_bom_to_utf8(file_path):
    # 读取带BOM的UTF-8文件内容
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        content = file.read()

    # 将内容写入不带BOM的UTF-8文件
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
convert_utf8_with_bom_to_utf8(os.path.join(data_dir, data_file))

# 排除函数
def exclude_row(row, rules):
    exclusion_reasons = []
    for rule in rules:
        field, operation = rule['field'], rule['operation']
        if operation == '==' and 'values' in rule and row[field] in rule['values']:
            exclusion_reasons.append((field, row[field]))
        elif operation == '==' and 'value' in rule and row[field] == rule['value']:
            exclusion_reasons.append((field, row[field]))
        elif operation == '>' and float(row[field]) > rule['value']:
            exclusion_reasons.append((field, row[field]))
        elif operation == '<' and float(row[field]) < rule['value']:
            exclusion_reasons.append((field, row[field]))
        elif operation == 'contains' and rule['value'] in row[field]:
            exclusion_reasons.append((field, row[field]))
    return exclusion_reasons if exclusion_reasons else False


# 读取CSV文件
with open(os.path.join("data", data_file), 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    headers = reader.fieldnames
    data = []
    excluded_data = []

    for row in reader:
        exclusion_reasons = exclude_row(row, exclusion_rules)
        if exclusion_reasons:
            excluded_data.append((row, exclusion_reasons))
        else:
            data.append(row)


# 排序函数
def sort_data(data, rules):
    for rule in rules:
        field = rule['field']
        data.sort(key=lambda x: x[field] or "", reverse=not rule['ascending'])
        for i, row in enumerate(data, 1):
            row[f'{field}_rank'] = i
            row[f'{field}_weight'] = rule['weight']


# 排序数据
sort_data(data, sorting_rules)

# 计算得分
for row in data:
    row['score'] = sum(int(row[f'{rule["field"]}_rank'])
                       * rule['weight'] for rule in sorting_rules)

# 最终排序
data.sort(key=itemgetter('score'))

result_headers = headers + \
    [f"{rule['field']}_rank" for rule in sorting_rules] + \
    [f"{rule['field']}_weight" for rule in sorting_rules] + ['score']

# 将排好序的数据写入到 result_filename
with open(result_filename, 'w', newline='', encoding='utf-8') as result_file:
    writer = csv.DictWriter(result_file, fieldnames=result_headers)
    writer.writeheader()
    writer.writerows(data)
    print("输出结果文件成功~")

# # 将排除的数据写入到 exclude_filename
exclude_headers = headers + ['排除原因字段', "排除原因值"]
with open(exclude_filename, 'w', newline='', encoding='utf-8') as exclude_file:
    writer = csv.DictWriter(exclude_file, fieldnames=exclude_headers)
    writer.writeheader()
    for row, reasons in excluded_data:
        row['排除原因字段'] = reasons[0][0]
        row['排除原因值'] = reasons[0][1]
        writer.writerow(row)
    print("输出排除文件成功~")


# 精简字段列表
simple_fields = ['转债代码', '转债名称', '最新价', '正股名称', '转股价值',
                   '转股溢价率', '转股溢价率_rank', '纯债溢价率', '纯债溢价率_rank',
                   '剩余规模(亿)', '剩余规模(亿)_rank',
                   '正股流通市值(亿)', '剩余年限', '强赎触发比例', 
                   '外部评级', '二级行业', '赎回状态', 'score']
with open(simple_filename, 'w', newline='', encoding='utf-8') as output_csv:
    writer = csv.DictWriter(output_csv, fieldnames=simple_fields)
    
    # 写入表头
    writer.writeheader()
    
    # 遍历输入文件的每一行
    for row in data:
        # 选择特定字段的值
        selected_values = {field: row[field] for field in simple_fields}
        
        # 写入选择的字段值到输出文件
        writer.writerow(selected_values)
    print("输出精简文件成功~")