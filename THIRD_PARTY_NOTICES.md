# 第三方模型与依赖说明

根目录 MIT LICENSE 适用于本项目的原创代码，不改变第三方组件和模型的许可。

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)：PP-OCRv4 检测、识别及 PP-OCRv2 方向分类预训练模型，上游 Apache-2.0。
- [RapidOCR](https://github.com/RapidAI/RapidOCR)：使用 rapidocr-onnxruntime 1.4.4 分发的本地 ONNX 模型与推理封装，Apache-2.0。
- ONNX Runtime、OpenCV、NumPy、Pillow、TkinterDnD2 及其他依赖分别适用其原始许可。
- Python 运行库的许可文本位于 `第三方许可/Python-3.10-LICENSE.txt`。
- PyInstaller 的许可及 bootloader exception 位于许可目录的 `distribution-notices/pyinstaller`，原创代码的 MIT 许可不替代该文件。

`第三方许可/模型来源.json` 记录模型名称、来源和 SHA-256。许可目录保留已有的许可与声明，并补充本次固定依赖分发包中的 LICENSE、COPYING 和 NOTICE 文件。
源码仓库不存放 ONNX 权重；安装固定版本的 RapidOCR 会安装模型。Windows 发行包将模型及所需许可随程序一起分发。
