<p align="center">
  <img src="assets/logo.svg" width="112" height="112" alt="hfget logo">
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

# hfget

**已完成。** 已验收 GGUF 完整分片选择和真实干跑入口。[验收范围与限制](COMPLETION.md)。

**找到你真正想要的 GGUF 量化版本，然后下载——分片、mmproj 和配套文件一并处理。**

*一个单文件 Python 命令行工具：在 Hugging Face 上按参数量预算搜索，用你自定义的规则给量化版本排序，再并行下载选中的结果。*

## 快速开始

需要 Python 3.9 或更高版本。

```sh
git clone https://github.com/ZisIsNotZis/hfget.git
cd hfget
python3 -m venv .venv && . .venv/bin/activate
pip install huggingface_hub requests
```

先修改 [`hfget.py`](hfget.py) 顶部的常量——搜索词、参数量上限、量化偏好、重试设置——然后预览并下载：

```sh
python3 hfget.py --dry-run
python3 hfget.py
```

`python3 hfget.py --help` 会列出可用参数。文件会进入 Hugging Face 的标准缓存目录；脚本本身不选择保存路径。

缺少 Hugging Face 客户端时，hfget 会直接报错退出；它不会自己换成假数据。

> 下载可能有数十 GB。请先看 dry-run 的输出，并确认磁盘剩余空间。

## 现在能做什么

- **在预算内搜索。** 按 `MAX_PARAM_FILTER`（默认 `max:36B`）搜索 Hugging Face 上的 `gguf` 模型，最多收集 `--target` 个可用结果。
- **按你的偏好排序。** 用有序正则规则优先匹配 `gsq-rco`、`ud`、`i-quant`、`q4` 等量化系列，并给 `xxs` / `xs` / `xl` 这类尺寸后缀加分。
- **处理分片，并且要求完整。** 把 `*-00001-of-00005.gguf` 形式的分片分组、按编号排序，只有整套齐全才接受。缺片、末尾缺片、编号重复、各片声明的 `of-NNNNN` 互相矛盾的分片组都会被跳过并打印原因，而不是下载半套——此时会改用完整且优先级稍低的量化。
- **过滤小文件。** 在得分相同的候选里，只保留体积大于中位数的那部分；如果一个都不剩，就保留全部。
- **挑选配套文件。** 按可配置的偏好选择 `mtp`、`dspark2` 和 `mmproj` 文件；如果主量化已内含 MTP，就不再单独选 MTP。配套文件不会抢走真正量化的主模型位置。
- **逐个预览。** `--dry-run` 会打印每个入选仓库及其文件列表，以及每个被拒绝的分片组的原因，不下载任何内容。
- **礼貌地下载。** API 失败会重试并等待，仓库之间有间隔，下载前有确认提示，并使用线程池（`--max-concurrent`，默认 4）。

## 架构

所有逻辑都刻意放在一个文件里：

```
hfget.py
├── CONFIG        搜索词、量化规则、尺寸/MTP/mmproj 偏好、重试参数
├── Discovery     list_models → pipeline 标签过滤 → model_info（失败重试）
├── Selection     group_shards → group_problem → score_main_quant → 中位数过滤 → 配套文件
└── Download      dry-run 报告、确认、ThreadPoolExecutor
```

没有包结构、安装步骤或隐藏入口：常量和脚本就是整个程序。项目范围与边界记录在 [`docs/project-status.md`](docs/project-status.md)。

## 如何开发

修改 [`hfget.py`](hfget.py) 里的常量，然后离线验证选择行为——无需联网、不下载权重、不用装任何依赖：

```sh
python3 selftest.py
```

它会用真实入口（`hfget.py --dry-run --offline-fixtures <临时状态>`）跑合成仓库，对每条承诺打印一行 `PASS`/`FAIL`，包括不完整分片组的拒绝原因。`hfget_offline.py` 只是 `huggingface_hub` 的测试替身，只能通过这个参数进入，会自己声明身份，并拒绝下载。

需要真实联网时，把范围收小：

```sh
python3 hfget.py --dry-run --target 5 --debug
```

项目没有构建步骤，也没有 CI。做实验时请把 `--target` 设小，并使用 `--dry-run`，避免为了测试选择逻辑而真的下载权重。

README 里的每条承诺都由 `selftest.py` 覆盖，唯一的例外是真实联网那一段——它需要一次 Hugging Face 请求，只能人工抽查。

## 如何贡献

欢迎提交 issue 和 pull request——范围、如何验证改动、什么样的 PR 更容易合入，都写在 [`CONTRIBUTING.md`](CONTRIBUTING.md) 里。

## 路线图

### 已实现

- 带参数量与 pipeline 标签过滤的模型发现。
- 量化打分、尺寸后缀排序和中位数过滤。
- 分片分组、完整集合校验与明确的拒绝原因。
- MTP、dspark2 和 mmproj 配套文件选择。
- dry-run 预览、重试与并行下载。
- 离线验收套件（`selftest.py`）覆盖选择承诺。
- 在脚本头部明确记录所有配置。

### 计划中

暂无进行中的里程碑。这是一个已收尾的个人工具：当前行为就是成品；只有当 Hugging Face API 或作者的工作流发生变化时，才会考虑改动。

### 未来设想

如果项目重新启动，方向仍然是：把“我该下载哪个 GGUF？”变成一条可信的命令。这可能意味着解释每个文件为什么被选中、下载前更可靠的体积报告，以及不需要改源码就能完成的配置——但不会长成一个包管理器或通用下载器。

## 许可证

[AGPL-3.0](LICENSE.md)。
