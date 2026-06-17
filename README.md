# 服装企业全链路经营诊断本地网页工具

这是一个本地运行的诊断工具。上传 Word、Excel、PDF、图片、CSV、文本资料后，系统会按《服装企业全链路穿透式经营诊断》的 16 个板块抽取证据、识别关键数据缺失，并生成完整交付包工作台。

## 启动

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

打开：

```text
http://127.0.0.1:8765
```

## ChatGPT 半自动增强

不配置 API Key 时，系统会使用本地规则诊断，可以直接运行。网页会自动生成一段可复制到 ChatGPT 的诊断提示词。

半自动增强流程：

1. 上传资料并完成本地诊断。
2. 打开“ChatGPT 半自动增强”模块，复制提示词。
3. 在 ChatGPT 中粘贴并生成 JSON 结果。
4. 回到网页，粘贴 JSON 并点击“合并到当前报告”。
5. 保存后导出 Word / PDF。

如果仍需 API 自动增强，也可以配置 `OPENAI_API_KEY`，但 API 调用会单独计费。

如果云端调用失败，系统会保留本地规则诊断结果。

## 诊断知识库

仓库已包含 `data/diagnosis_knowledge.json` 作为默认诊断知识库，可以直接运行。

如需从原始 Word 文档重新生成知识库，可将文档放在项目根目录并命名为 `服装企业全链路穿透式经营诊断.docx`，或设置环境变量：

```bash
export DIAGNOSIS_KNOWLEDGE_DOCX="/path/to/服装企业全链路穿透式经营诊断.docx"
```

## 支持输入

- Word：`.docx`
- Excel：`.xlsx`、`.xlsm`
- PDF：`.pdf`
- 图片：`.png`、`.jpg`、`.jpeg`、`.webp`、`.bmp`
- 文本：`.txt`、`.md`、`.csv`

图片会记录文件名、尺寸和 OCR 状态；当前机器未安装 `tesseract` 时会提示补充文字版资料。PDF 如果像扫描件一样抽不出文字，也会在资料包里标记为疑似扫描 PDF。

## 输出

- 完整交付包工作台
- 诊断报告预览
- 4 条流程与 6 个经营主线判断
- 16 个板块可展开诊断明细
- 部门诊断问题清单
- 关键数据缺失清单
- 可编辑的核心问题、根因分析、90 天计划
- Word 报告导出
- PDF 报告导出

上传文件保存在 `data/uploads/`，分析结果和导出文件保存在 `data/reports/`。
