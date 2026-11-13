多中心项目目录服务。现有中心适配、协议谱系、去重和资料时效处理生成联合目录，不包含临床个体决策。

环境：Linux，Python 3.11.2 或更新的兼容版本。所有依赖来自 Python 标准库，无需安装第三方包。

测试：python3 -m unittest discover -s tests/federated_trials -p 'test_*.py'
构建：python3 -m compileall -q trial_site_federator
验收：python3 -m trial_site_federator.console.federate fixtures/demo.json --db /tmp/trial_site_federator-acceptance.sqlite3

目录：trial_site_federator 保存业务处理与存储模块；tests/federated_trials 保存业务回归；fixtures/demo.json 为原有业务样例，fixtures/analysis 为经营分析资料及字段说明。

原有验收命令每次使用新的 SQLite 路径，避免复用上次状态。新增输入完整性检查：
python3 -m unittest discover -s tests/analysis_inputs -v

招募可行性分析（仅用于中心资源排期，不用于判断病人是否符合临床条件）：
python3 -m trial_site_federator.feasibility --input fixtures/analysis/input.json --database /tmp/feasibility.sqlite3 --output /tmp/feasibility.json
模型说明：以开放天数为曝光单位；只用已结束、已上报且 as_of 前已知的月份训练；as_of 当月与开放天数为零的停招月不计入速率；跨协议仅在目录谱系判定可合并时合并；中心冷启动借分段/项目先验并放宽区间；过度离散按 NB2 估计，否则退回 Poisson 加费率不确定性；总量与达标概率来自同一次联合模拟，不把各中心概率相加。回测采用滚动起点，并与简单速率基线和日历月均值基线比较。同一 (model_id, as_of) 只保留一个分析版本，更正上月开放天数后重跑会在 revision_context 中列出变更字段、前后总量与概率差异。无法识别的中心/协议单独给出原因，不按零人计入。

容器运行可使用已经预装的 ccusr/prepared:3f007a95fcee-4441968e5ff6 镜像；将当前仓库只读挂载至 /source，在容器内复制到 /tmp/product 后运行上述命令。依赖准备和正式运行分离，运行过程中不需要网络访问。
