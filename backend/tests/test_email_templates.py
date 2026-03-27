import os
import re


TEMPLATE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "app", "core", "emails", "templates"
)


class TestEmailTemplates:
    def test_password_reset_has_table_button(self):
        """Password reset should use table-based button, not bare <a>"""
        with open(os.path.join(TEMPLATE_DIR, "password_reset.html"), encoding="utf-8") as f:
            content = f.read()
        assert "role=\"presentation\"" in content, "Button should be table-based for email compatibility"
        assert "background-color: #4CAF50" in content, "Button should have inline background color"

    def test_login_otp_has_inline_styles(self):
        """Login OTP template should have inline styles on all <p> tags"""
        with open(os.path.join(TEMPLATE_DIR, "login_otp.html"), encoding="utf-8") as f:
            content = f.read()
        p_tags = re.findall(r"<p[^>]*>", content)
        for tag in p_tags:
            assert "style=" in tag, f"Missing inline style on: {tag}"

    def test_account_lockout_has_inline_styles(self):
        """Account lockout template should have inline styles"""
        with open(os.path.join(TEMPLATE_DIR, "account_lockout.html"), encoding="utf-8") as f:
            content = f.read()
        p_tags = re.findall(r"<p[^>]*>", content)
        for tag in p_tags:
            assert "style=" in tag, f"Missing inline style on: {tag}"
        li_tags = re.findall(r"<li[^>]*>", content)
        for tag in li_tags:
            assert "style=" in tag, f"Missing inline style on: {tag}"

    def test_activation_template_unchanged(self):
        """Activation template should still have table-based button (was already correct)"""
        with open(os.path.join(TEMPLATE_DIR, "activation.html"), encoding="utf-8") as f:
            content = f.read()
        assert "role=\"presentation\"" in content
        assert "Activate Account" in content
