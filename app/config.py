from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
TITLE = '零售退货优惠分摊与累计退款限额核验'
SHORT = 'returnbook'
VERSION = '2026.11.1'
COLUMNS = ['event_id', 'order_id', 'kind', 'sku', 'quantity', 'unit_price', 'discount', 'shipping', 'currency', 'time', 'note']
PAGES = [('intake', '订单采信'), ('contract', '促销契约'), ('model', '优惠分摊'), ('calculate', '退款核算'), ('quarantine', '争议隔离'), ('reconcile', '支付对账'), ('batches', '批次复核')]
MAX_BYTES = 2_000_000
MAX_ROWS = 10000
NULLS = frozenset(['', '-', 'N/A', 'NULL', '未知'])
