REASONS = {'COLUMN_COUNT': '字段数量错误', 'NULL_VALUE': '必填值缺失', 'NUMBER': '金额或数量无效', 'CURRENCY': '只接受CNY订单', 'TIME': '时间缺少偏移', 'KIND': '未知事件类型', 'DUPLICATE': '重复事件剔除', 'CONFLICT': '事件号存在异值', 'ORDER_PROMO': '订单优惠不一致或超额', 'SKU_CONFLICT': '订单内商品重复', 'ORDER_MISSING': '原订单不存在', 'SKU_MISSING': '原订单无此商品', 'OVER_REFUND': '退货数量超过剩余数量', 'BEFORE_SALE': '退货早于销售', 'TOO_MANY_UNITS': '订单件数超过上限'}
def issue(row, code, detail=''):
    return {'line': row.get('line', 0), 'code': code, 'detail': detail or REASONS.get(code, code), 'raw': row.get('raw', row)}
