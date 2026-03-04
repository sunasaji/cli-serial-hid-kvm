"""Tests for OCR postprocessing (no Tesseract required)."""

from cli_serial_hid_kvm.ocr import TerminalOCR


class TestPostprocessText:
    def setup_method(self):
        # Create instance without initializing tesseract
        self.ocr = TerminalOCR.__new__(TerminalOCR)

    def test_strips_trailing_whitespace(self):
        result = self.ocr._postprocess_text("hello   \nworld  \n")
        assert result == "hello\nworld"

    def test_collapses_excessive_newlines(self):
        result = self.ocr._postprocess_text("a\n\n\n\n\n\nb")
        assert result == "a\n\n\nb"

    def test_corrects_pipe_s_to_ls(self):
        result = self.ocr._postprocess_text("$ |s -la\n")
        assert result == "$ ls -la"

    def test_corrects_pipe_s_at_line_start(self):
        result = self.ocr._postprocess_text("\n|s -la")
        assert result == "ls -la"

    def test_preserves_normal_text(self):
        text = "hello world\nfoo bar"
        result = self.ocr._postprocess_text(text)
        assert result == text

    def test_empty_input(self):
        result = self.ocr._postprocess_text("")
        assert result == ""
