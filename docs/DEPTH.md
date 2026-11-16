# 零售退货优惠分摊与累计退款限额核验 深度登记

使用者：零售财务数据专员。核心规则：订单级优惠以最大余额法分至商品最小单位，部分退货按原分摊反向回收，累计退款不超过实付，运费只在规则满足时退一次。

## 功能模块
| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 订单采信 | 执行订单采信并复核证据 | `GET /intake` `POST /api/intake` | `app/modules/m1_intake/service.py` `app/modules/m1_intake/rules.py` | `tests/test_intake.py` |
| M2 促销契约 | 执行促销契约并复核证据 | `GET /contract` `POST /api/contract` | `app/modules/m2_contract/service.py` `app/modules/m2_contract/rules.py` | `tests/test_contract.py` |
| M3 优惠分摊 | 执行优惠分摊并复核证据 | `GET /model` `POST /api/model` | `app/modules/m3_model/service.py` `app/modules/m3_model/rules.py` | `tests/test_model.py` |
| M4 退款核算 | 执行退款核算并复核证据 | `GET /calculate` `POST /api/calculate` | `app/modules/m4_calculate/service.py` `app/modules/m4_calculate/rules.py` | `tests/test_calculate.py` |
| M5 争议隔离 | 执行争议隔离并复核证据 | `GET /quarantine` `POST /api/quarantine` | `app/modules/m5_quarantine/service.py` `app/modules/m5_quarantine/rules.py` | `tests/test_quarantine.py` |
| M6 支付对账 | 执行支付对账并复核证据 | `GET /reconcile` `POST /api/reconcile` | `app/modules/m6_reconcile/service.py` `app/modules/m6_reconcile/rules.py` | `tests/test_reconcile.py` |
| M7 批次复核 | 执行批次复核并复核证据 | `GET /batches` `POST /api/batches` | `app/modules/m7_batches/service.py` `app/modules/m7_batches/rules.py` | `tests/test_batches.py` |

## 陷阱登记
| TRAP | 现象 | 朴素实现 | 处理 | 位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | 历史编码 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m1_intake/rules.py` | `tests/test_intake.py::test_legacy_chinese_data` |
| TRAP-02 | BOM表头 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m1_intake/rules.py` | `tests/test_intake.py::test_sample_bom_header` |
| TRAP-06 | 数字归一 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_sample_money_normalized` |
| TRAP-07 | 缺失哨兵 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_missing_price_not_zero` |
| TRAP-08 | 编码保形 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_sample_leading_order_preserved` |
| TRAP-10 | 精确金额 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m2_contract/rules.py` | `tests/test_contract.py::test_decimal_cents_exact` |
| TRAP-14 | 重复异值 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m3_model/rules.py` | `tests/test_model.py::test_sample_duplicate_reason` |
| TRAP-23 | 区间端点 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m4_calculate/rules.py` | `tests/test_calculate.py::test_unit_slices_do_not_overlap` |
| TRAP-24 | 舍入尾差 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/modules/m3_model/rules.py` | `tests/test_model.py::test_largest_remainder_counterexample` |
| TRAP-26 | 陈旧版本 | 直接转换或覆盖产生误判 | 按数据字典处理并保留来源证据 | `app/store.py` | `tests/test_batches.py::test_sample_old_review_rejected` |

## 对账规则
优惠分摊守恒；实付=已退+剩余可退；拒绝退款不改累计

## 已知不覆盖
不覆盖换货补差价、积分抵现、多币种汇率与外部支付退款；文件内须包含完整原销售单及售后事件，跨文件结果不自动串接。

## 证据
每个事件保留CSV逻辑记录结束行号与原值；隔离记录附原因码。运行摘要包含输入SHA256、规则版本、参数和耗时。持久化为单次事务；重复输入复用运行ID。
