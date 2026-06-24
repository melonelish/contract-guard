"""Test draft review functionality."""

import pytest
from app.services.review import _html_to_text


class TestHTMLToText:
    """Test HTML to plain text conversion for draft review."""

    def test_simple_paragraph(self):
        html = "<p>这是一个段落</p>"
        result = _html_to_text(html)
        assert result == "这是一个段落"

    def test_multiple_paragraphs(self):
        html = "<p>第一段</p><p>第二段</p>"
        result = _html_to_text(html)
        assert "第一段" in result
        assert "第二段" in result
        assert result.count("\n") >= 1  # Should have newlines between paragraphs

    def test_headings(self):
        html = "<h1>标题一</h1><h2>标题二</h2><p>正文</p>"
        result = _html_to_text(html)
        assert "标题一" in result
        assert "标题二" in result
        assert "正文" in result

    def test_list_items(self):
        html = "<ul><li>项目一</li><li>项目二</li></ul>"
        result = _html_to_text(html)
        assert "项目一" in result
        assert "项目二" in result

    def test_br_tags(self):
        html = "<p>第一行<br>第二行<br/>第三行</p>"
        result = _html_to_text(html)
        assert "第一行" in result
        assert "第二行" in result
        assert "第三行" in result

    def test_html_entities(self):
        html = "<p>Test &nbsp; &lt;tag&gt; &amp; &quot;quote&quot;</p>"
        result = _html_to_text(html)
        assert " " in result  # &nbsp; -> space
        assert "<tag>" in result
        assert "&" in result
        assert '"quote"' in result

    def test_nested_tags(self):
        html = "<div><p><strong>粗体</strong>和<em>斜体</em></p></div>"
        result = _html_to_text(html)
        assert "粗体" in result
        assert "斜体" in result
        assert "<strong>" not in result
        assert "<em>" not in result

    def test_remove_all_tags(self):
        html = "<div><span><a href='#'>链接</a></span></div>"
        result = _html_to_text(html)
        assert "链接" in result
        assert "<" not in result
        assert ">" not in result

    def test_collapse_multiple_newlines(self):
        html = "<p>段落一</p><p></p><p></p><p>段落二</p>"
        result = _html_to_text(html)
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result

    def test_empty_html(self):
        html = ""
        result = _html_to_text(html)
        assert result == ""

    def test_only_tags_no_content(self):
        html = "<div><p></p><span></span></div>"
        result = _html_to_text(html)
        assert result.strip() == ""

    def test_tiptap_like_structure(self):
        """Test realistic TipTap editor output."""
        html = """
        <h2>合同条款</h2>
        <p>甲方：<strong>北京XX公司</strong></p>
        <p>乙方：<strong>上海YY公司</strong></p>
        <h3>第一条 合同标的</h3>
        <p>本合同标的为软件开发服务。</p>
        <ul>
          <li>需求分析</li>
          <li>系统设计</li>
          <li>编码实现</li>
        </ul>
        <h3>第二条 付款条件</h3>
        <p>付款分三期进行：</p>
        <ol>
          <li>首付款30%</li>
          <li>中期款50%</li>
          <li>尾款20%</li>
        </ol>
        """
        result = _html_to_text(html)

        # Check main content preserved
        assert "合同条款" in result
        assert "甲方" in result
        assert "北京XX公司" in result
        assert "第一条 合同标的" in result
        assert "软件开发服务" in result
        assert "需求分析" in result
        assert "付款条件" in result
        assert "首付款30%" in result

        # Check structure somewhat preserved (newlines between sections)
        assert result.count("\n") > 5

    def test_contract_with_special_characters(self):
        html = "<p>违约金不超过合同总价的20%，最高不超过50万元。</p>"
        result = _html_to_text(html)
        assert "违约金不超过合同总价的20%" in result
        assert "50万元" in result
