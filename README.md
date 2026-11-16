# 零售退货优惠分摊与累计退款限额核验

供零售财务数据专员核对全角金额、重复退货、超量退货、尾差、混币等数据问题。订单级优惠以最大余额法分至商品最小单位，部分退货按原分摊反向回收，累计退款不超过实付，运费只在规则满足时退一次。

## 启动

```sh
docker compose up --build -d
```

访问 [工作台](http://localhost:18208/)，无需准备文件即可运行。

## 演示

1. 进入采信模块，选脏样例并运行。
2. 逐模块核对来源行、业务结果与隔离原因。
3. 切换干净样例比较差异；重复运行相同输入复用批次。
4. 对账通过后进入归档模块复核，可下载隔离证据CSV。

## 模块与入口

- 订单采信：`/intake`，`GET/POST /api/intake`。
- 促销契约：`/contract`，`GET/POST /api/contract`。
- 优惠分摊：`/model`，`GET/POST /api/model`。
- 退款核算：`/calculate`，`GET/POST /api/calculate`。
- 争议隔离：`/quarantine`，`GET/POST /api/quarantine`。
- 支付对账：`/reconcile`，`GET/POST /api/reconcile`。
- 批次复核：`/batches`，`GET/POST /api/batches`。

[接口文档](http://localhost:18208/docs)。

## 验证

```sh
docker compose config --quiet
docker compose exec -T app pytest -q
```

## 数据与定义

仅处理CNY；所有金额先用Decimal检查精度，再以整数分计算，不进行浮点累加。销售行须有正数量和单价，同订单的整单优惠与运费重复填写但只计算一次。同单SKU唯一，件数上限10000。整单优惠按每件单价最大余额分摊，余数相同时按SKU及件序确定。退货按原件序回收原实付，已退单位不重复使用；全部件数退完才返运费一次。退货按UTC与事件号排序，早于销售或超过数量的退货隔离且不改变已退款累计。

定义见 `docs/DATA-DICTIONARY.md`，模块和测试映射见 `docs/DEPTH.md`。样例位于 `sample_data/`。SQLite存放于命名卷，重启保留批次。确认不再需要历史记录时，可用 `docker compose down -v` 重建数据。

## 已知范围

不覆盖换货补差价、积分抵现、多币种汇率与外部支付退款；文件内须包含完整原销售单及售后事件，跨文件结果不自动串接。

单字段金额上限为1000000000000元，超过上限返回字段错误。
