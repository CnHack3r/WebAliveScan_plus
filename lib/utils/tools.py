from lib.common.output import Output


def save_result(path, headers, results):
    import csv
    try:
        # 使用UTF-8编码保存CSV文件，避免中文乱码
        with open(path, 'w', encoding='utf-8', errors='ignore', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for result in results:
                # 确保所有值都是字符串，并且处理特殊字符
                row = {}
                for h in headers:
                    value = result.get(h, '')
                    # 如果是列表，转换为字符串
                    if isinstance(value, list):
                        value = ','.join(value)
                    row[h] = str(value).replace('"', '""')
                writer.writerow(row)
            return True
    except Exception as e:
        Output().error(f"保存结果失败: {e}")
        return False
