"""
PDF 生成工具模块
使用 fpdf2 生成 PDF，支持中文字体
如果 fpdf2 不可用，自动降级为保存 .txt 文件
"""
import os
import re
import platform
import logging

logger = logging.getLogger(__name__)

CHINESE_FONT_PATHS = {
    "Windows": [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ],
    "Linux": [
        "/usr/share/fonts/truetype/chinese/SarasaMonoSC-Regular.ttf",
        "/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf",
        "/usr/share/fonts/truetype/chinese/NotoSansSC[wght].ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ],
    "Darwin": [
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ],
}

# Emoji 和特殊符号过滤正则：
# 匹配 BMP 之外的所有字符（emoji 如 ✅📥🤖等，code point > 0xFFFF）
# 以及 BMP 内的特殊符号（Dingbats、Misc Symbols 等）
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # 表情符号
    "\U0001F300-\U0001F5FF"  # 杂项符号和象形文字
    "\U0001F680-\U0001F6FF"  # 交通和地图符号
    "\U0001F1E0-\U0001F1FF"  # 旗帜
    "\U00002702-\U000027B0"  # Dingbats (✅✓✗等)
    "\U000024C2-\U0001F251"  # Enclosed characters
    "\U0001f900-\U0001f9FF"  # 补充表情符号
    "\U0001fa00-\U0001fa6F"  # Chess symbols
    "\U0001fa70-\U0001faFF"  # Symbols and Pictographs Extended-A
    "\U00002600-\U000026FF"  # Misc symbols (☀☁☂等)
    "\U00002700-\U000027BF"  # Dingbats
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0000200D"             # Zero Width Joiner
    "\U00002B50"             # ⭐
    "\U000023E9-\U000023F3"  # Misc symbols (⏩⏪⏭⏮⏯等)
    "\U000023F0-\U000023FA"  # ⏰⏱⏲⏳
    "\U000025AA-\U000025FE"  # 几何形状
    "\U00002934-\U00002935"  # ⤴⤵
    "\U00002B05-\U00002B07"  # ⬅⬆⬇
    "]+"
)


def _strip_emoji(text: str) -> str:
    """移除文本中的 emoji 和字体不支持的特殊字符，替换为 [x] 标记"""
    # 先移除完整的 emoji 序列
    cleaned = _EMOJI_RE.sub("", text)
    # 再移除剩余的非 BMP 字符（超出基本多文种平面的字符）
    cleaned = "".join(c for c in cleaned if ord(c) <= 0xFFFF)
    return cleaned


def find_chinese_font():
    """查找系统中可用的中文字体"""
    system = platform.system()
    for path in CHINESE_FONT_PATHS.get(system, []):
        if os.path.exists(path):
            return path
    return None


def generate_pdf(text, output_path, title="修改后的文档"):
    """
    生成 PDF 文件

    Args:
        text: 文本内容
        output_path: 输出路径
        title: 文档标题

    Returns:
        tuple: (success: bool, actual_path: str)
            如果 PDF 生成成功，返回 (True, pdf_path)
            如果降级为 txt，返回 (True, txt_path)
    """
    try:
        from fpdf import FPDF
    except ImportError:
        logger.warning("fpdf2 未安装，降级为 txt 文件")
        return _save_as_txt(text, output_path)

    font_path = find_chinese_font()
    if not font_path:
        logger.warning("未找到中文字体，降级为 txt 文件")
        return _save_as_txt(text, output_path)

    try:
        pdf = FPDF()
        pdf.font_subsetting = False  # 关闭字体子集化，避免 MERG/subset 错误
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # 添加中文字体
        pdf.add_font("ChineseFont", "", font_path)
        pdf.set_font("ChineseFont", "", 12)

        # 写入内容（预处理移除emoji）
        text = _strip_emoji(text)
        for line in text.split("\n"):
            if not line.strip():
                pdf.ln(6)
                continue
            pdf.multi_cell(0, 7, line)

        pdf.output(output_path)
        return True, output_path

    except Exception as e:
        logger.error(f"PDF 生成失败: {e}，降级为 txt 文件")
        return _save_as_txt(text, output_path)


def generate_chat_pdf(messages: list, session_id: str) -> bytes:
    """
    生成对话导出 PDF（返回 bytes）

    Args:
        messages: 对话消息列表 [{"role": "user"/"assistant", "content": "..."}]
        session_id: 会话 ID

    Returns:
        PDF 文件的 bytes 内容
    """
    from fpdf import FPDF

    font_path = find_chinese_font()
    if not font_path:
        raise RuntimeError("未找到中文字体，无法生成 PDF")

    pdf = FPDF()
    pdf.font_subsetting = False  # 关闭字体子集化，避免 MERG/subset 错误
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # 添加中文字体
    pdf.add_font("ChineseFont", "", font_path)
    pdf.set_font("ChineseFont", "", 12)

    # 标题
    pdf.set_font("ChineseFont", "", 16)
    pdf.cell(0, 12, "DocAgent 对话记录", ln=True, align="C")
    pdf.set_font("ChineseFont", "", 10)
    pdf.cell(0, 8, f"Session: {session_id[:12]}", ln=True, align="C")
    pdf.ln(8)

    # 写入对话内容
    for msg in messages:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg.get("content", "")

        # 预处理：移除 emoji 和字体不支持的字符
        content = _strip_emoji(content)

        # 角色标签
        pdf.set_font("ChineseFont", "", 11)
        if msg["role"] == "user":
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, f"  {role}：", ln=True, fill=True)
        else:
            pdf.set_fill_color(245, 245, 255)
            pdf.cell(0, 8, f"  {role}：", ln=True, fill=True)

        # 内容
        pdf.set_font("ChineseFont", "", 10)
        for line in content.split("\n"):
            if not line.strip():
                pdf.ln(3)
                continue
            _safe_write_line(pdf, line)

        pdf.ln(4)

    # 输出为 bytes
    return pdf.output()


def _safe_write_line(pdf, line: str, indent: str = "  "):
    """
    安全地将一行文本写入PDF，处理超长行和特殊字符

    fpdf2 的 multi_cell 在遇到无法换行的长字符时会抛出
    "Not enough horizontal space" 异常，这里做逐字符安全写入
    """
    text = indent + line
    try:
        pdf.multi_cell(0, 6, text)
    except Exception:
        # 降级：逐段写入，每段不超过80字符
        while text:
            chunk = text[:80]
            text = text[80:]
            try:
                pdf.multi_cell(0, 6, chunk)
            except Exception:
                # 最终降级：跳过无法渲染的字符
                safe_chunk = "".join(
                    c for c in chunk if ord(c) < 0x10000 and c.isprintable() or c in " \t"
                )
                if safe_chunk.strip():
                    try:
                        pdf.multi_cell(0, 6, safe_chunk)
                    except Exception:
                        pass  # 跳过完全无法渲染的行


def _save_as_txt(text, output_path):
    """降级方案：保存为 txt 文件"""
    if output_path.lower().endswith(".pdf"):
        output_path = output_path[:-4] + ".txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return True, output_path
