def write_to_csv(restaurant_list: list):
    """
    お店リストをCSVに保存
    :param restaurant_list:
    :return:
    """
    with open('column_list.csv') as f:
        column_list = [row.strip() for row in f]

    with open('attack_list.csv', 'w') as f:
        f.write(','.join(column_list) + '\n')

        for restaurant in restaurant_list:
            row = [restaurant[col] for col in column_list]
            f.write(','.join(row))
