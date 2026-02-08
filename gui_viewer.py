# -*- coding: utf-8 -*-
"""
Linux 内核中国公司贡献分析 GUI 工具
主应用程序
"""

import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QLabel,
    QLineEdit, QComboBox, QPushButton, QMenu, QMessageBox, QDialog,
    QTextBrowser, QProgressBar, QStatusBar, QFrame, QTabWidget,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import QAction, QFont, QColor, QDesktopServices, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置 matplotlib 中文字体
rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

from translations import (
    translate_category, translate_score_dimension, translate_subsystem_tier,
    get_ui_text, get_category_for_group, translate_company_name,
    CATEGORY_TRANSLATIONS, SCORE_DIMENSION_TRANSLATIONS,
    TECHNICAL_SCORE_TRANSLATIONS, IMPACT_SCORE_TRANSLATIONS,
    QUALITY_SCORE_TRANSLATIONS, COMMUNITY_SCORE_TRANSLATIONS
)


@dataclass
class CompanyData:
    """公司数据结构"""
    name: str
    commit_count: int
    total_score: int
    avg_score: float
    max_score: int
    min_score: int
    categories: Dict[str, int]


class DiffHighlighter(QSyntaxHighlighter):
    """Git 风格的 diff 语法高亮"""

    def __init__(self, document: QTextDocument):
        super().__init__(document)

    def highlightBlock(self, text: str):
        """高亮一行文本"""
        # 删除行（红色）
        if text.startswith('-') and not text.startswith('---'):
            format = QTextCharFormat()
            format.setForeground(QColor('#e74c3c'))  # 红色
            format.setBackground(QColor('#fadbd8'))  # 浅红色背景
            self.setFormat(0, len(text), format)

        # 新增行（绿色）
        elif text.startswith('+') and not text.startswith('+++'):
            format = QTextCharFormat()
            format.setForeground(QColor('#27ae60'))  # 绿色
            format.setBackground(QColor('#d5f4e6'))  # 浅绿色背景
            self.setFormat(0, len(text), format)

        # diff 头部（蓝色）
        elif text.startswith('@@') or text.startswith('diff --git') or \
             text.startswith('index ') or text.startswith('--- ') or text.startswith('+++ '):
            format = QTextCharFormat()
            format.setForeground(QColor('#2980b9'))  # 蓝色
            format.setFontWeight(QFont.Weight.Bold)
            self.setFormat(0, len(text), format)

        # 文件路径（紫色）
        elif text.startswith('a/') or text.startswith('b/'):
            format = QTextCharFormat()
            format.setForeground(QColor('#8e44ad'))  # 紫色
            self.setFormat(0, len(text), format)


class DataLoader:
    """数据加载器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.commits_df: Optional[pd.DataFrame] = None
        self.companies: Dict[str, CompanyData] = {}
        self.all_summary_files: List[Path] = []
        self.all_jsonl_files: List[Path] = []

    def find_data_files(self) -> bool:
        """查找所有数据文件"""
        self.all_jsonl_files = sorted(self.data_dir.glob("chinese_companies_*.jsonl"))
        self.all_summary_files = sorted(self.data_dir.glob("chinese_companies_*_summary.json"))
        return len(self.all_jsonl_files) > 0

    def load_commits(self) -> pd.DataFrame:
        """加载所有提交数据"""
        all_commits = []

        for jsonl_file in self.all_jsonl_files:
            try:
                # 使用 pandas 读取 JSONL 文件，每行一个 JSON 对象
                df = pd.read_json(jsonl_file, lines=True)
                all_commits.append(df)
            except Exception as e:
                print(f"读取文件 {jsonl_file} 时出错: {e}")

        if all_commits:
            self.commits_df = pd.concat(all_commits, ignore_index=True)
            # 确保日期字段是 datetime 类型，使用 UTC 时区处理混合时区
            if 'author_date' in self.commits_df.columns:
                self.commits_df['author_date'] = pd.to_datetime(self.commits_df['author_date'], errors='coerce', utc=True)
            if 'commit_date' in self.commits_df.columns:
                self.commits_df['commit_date'] = pd.to_datetime(self.commits_df['commit_date'], errors='coerce', utc=True)

        return self.commits_df

    def load_summaries(self) -> Dict[str, CompanyData]:
        """加载汇总数据"""
        companies = {}

        for summary_file in self.all_summary_files:
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)

                for company_name, company_data in summary.get('companies', {}).items():
                    if company_name not in companies:
                        companies[company_name] = CompanyData(
                            name=company_name,
                            commit_count=0,
                            total_score=0,
                            avg_score=0.0,
                            max_score=0,
                            min_score=float('inf'),
                            categories={}
                        )

                    # 累加数据
                    companies[company_name].commit_count += company_data.get('commit_count', 0)
                    companies[company_name].total_score += company_data.get('total_score', 0)

                    # 合并分类
                    for cat, count in company_data.get('categories', {}).items():
                        companies[company_name].categories[cat] = \
                            companies[company_name].categories.get(cat, 0) + count

            except Exception as e:
                print(f"读取汇总文件 {summary_file} 时出错: {e}")

        # 计算平均分
        for company in companies.values():
            if company.commit_count > 0:
                company.avg_score = company.total_score / company.commit_count

        # 计算最大最小分数（从提交数据中）
        if self.commits_df is not None and not self.commits_df.empty:
            for company_name in companies:
                company_commits = self.commits_df[self.commits_df['author_company'] == company_name]
                if not company_commits.empty:
                    companies[company_name].max_score = company_commits['score_total'].max()
                    companies[company_name].min_score = company_commits['score_total'].min()
                else:
                    companies[company_name].min_score = 0

        self.companies = companies
        return companies

    def get_commits_by_company(self, company_name: str) -> pd.DataFrame:
        """获取指定公司的提交记录"""
        if self.commits_df is None:
            return pd.DataFrame()

        return self.commits_df[self.commits_df['author_company'] == company_name].copy()


class CommitDetailDialog(QDialog):
    """提交详情对话框"""

    def __init__(self, commit_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.commit_data = commit_data
        self.setWindowTitle(f"{get_ui_text('analysis_result')} - {commit_data.get('short_hash', '')}")
        self.setMinimumSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 创建标签页
        tabs = QTabWidget()

        # 基本信息标签页
        info_tab = self.create_info_tab()
        tabs.addTab(info_tab, "基本信息")

        # 评分详情标签页
        score_tab = self.create_score_tab()
        tabs.addTab(score_tab, "评分详情")

        # 分类标签页
        category_tab = self.create_category_tab()
        tabs.addTab(category_tab, "分类信息")

        layout.addWidget(tabs)

        # 关闭按钮
        close_btn = QPushButton(get_ui_text('close'))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def create_info_tab(self) -> QWidget:
        """创建基本信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 创建文本浏览器显示信息
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)

        html = self._generate_info_html()
        browser.setHtml(html)

        layout.addWidget(browser)
        widget.setLayout(layout)
        return widget

    def _generate_info_html(self) -> str:
        """生成基本信息HTML"""
        commit = self.commit_data

        html = f"""
        <h2>基本信息</h2>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr><td><b>提交哈希</b></td><td>{commit.get('commit_hash', 'N/A')}</td></tr>
        <tr><td><b>短哈希</b></td><td>{commit.get('short_hash', 'N/A')}</td></tr>
        <tr><td><b>作者</b></td><td>{commit.get('author_name', 'N/A')} &lt;{commit.get('author_email', 'N/A')}&gt;</td></tr>
        <tr><td><b>作者公司</b></td><td>{commit.get('author_company', 'N/A')}</td></tr>
        <tr><td><b>作者日期</b></td><td>{commit.get('author_date', 'N/A')}</td></tr>
        <tr><td><b>提交者</b></td><td>{commit.get('committer_name', 'N/A')} &lt;{commit.get('committer_email', 'N/A')}&gt;</td></tr>
        <tr><td><b>提交者公司</b></td><td>{commit.get('committer_company', 'N/A')}</td></tr>
        <tr><td><b>提交日期</b></td><td>{commit.get('commit_date', 'N/A')}</td></tr>
        <tr><td><b>主题</b></td><td>{commit.get('subject', 'N/A')}</td></tr>
        """

        # 添加子系统信息
        if 'subsystem_prefix' in commit:
            html += f"<tr><td><b>子系统</b></td><td>{commit.get('subsystem_prefix', 'N/A')}</td></tr>"
        if 'subsystems_touched' in commit:
            subsystems = ', '.join(commit.get('subsystems_touched', []))
            html += f"<tr><td><b>涉及子系统</b></td><td>{subsystems}</td></tr>"
        if 'subsystem_tier' in commit:
            tier = commit.get('subsystem_tier', 6)
            tier_name = translate_subsystem_tier(tier)
            html += f"<tr><td><b>子系统层级</b></td><td>{tier_name}</td></tr>"

        # 添加文件变更信息
        if 'files_changed' in commit:
            html += f"<tr><td><b>文件变更</b></td><td>{commit.get('files_changed', 0)} 个文件</td></tr>"
        if 'insertions' in commit:
            html += f"<tr><td><b>新增行数</b></td><td>{commit.get('insertions', 0)}</td></tr>"
        if 'deletions' in commit:
            html += f"<tr><td><b>删除行数</b></td><td>{commit.get('deletions', 0)}</td></tr>"

        # 添加链接
        if 'link' in commit:
            link = commit.get('link', '')
            html += f"<tr><td><b>链接</b></td><td><a href=\"{link}\">{link}</a></td></tr>"

        # 添加 CVE ID
        if commit.get('cve_ids'):
            cve_list = ', '.join(commit.get('cve_ids', []))
            html += f"<tr><td><b>CVE ID</b></td><td>{cve_list}</td></tr>"

        # 添加 Fixes 标签
        if commit.get('fixes_tag'):
            html += f"<tr><td><b>Fixes</b></td><td>{commit.get('fixes_tag', '')}</td></tr>"

        # 添加稳定版本标记
        if commit.get('cc_stable'):
            html += f"<tr><td><b>CC: Stable</b></td><td>是</td></tr>"

        # 添加标志
        if commit.get('flags'):
            flags = ', '.join(commit.get('flags', []))
            html += f"<tr><td><b>标志</b></td><td>{flags}</td></tr>"

        html += "</table>"

        return html

    def create_score_tab(self) -> QWidget:
        """创建评分详情标签页"""
        widget = QWidget()
        layout = QVBoxLayout()

        browser = QTextBrowser()
        html = self._generate_score_html()
        browser.setHtml(html)

        layout.addWidget(browser)
        widget.setLayout(layout)
        return widget

    def _generate_score_html(self) -> str:
        """生成评分详情HTML"""
        commit = self.commit_data

        html = "<h2>评分详情</h2>"

        # 总分
        html += f"<h3>总分: {commit.get('score_total', 0)}</h3>"

        # 各维度分数
        html += "<table border=\"1\" cellpadding=\"5\" cellspacing=\"0\" style=\"border-collapse: collapse;\">"
        html += "<tr><th><b>维度</b></th><th><b>分数</b></th></tr>"

        for dim in ['score_technical', 'score_impact', 'score_quality', 'score_community']:
            dim_name = translate_score_dimension(dim)
            dim_score = commit.get(dim, 0)
            html += f"<tr><td>{dim_name}</td><td>{dim_score}</td></tr>"

        html += "</table><br>"

        # 详细细分
        breakdown = commit.get('score_breakdown', {})

        # 技术评分细分
        if 'technical' in breakdown:
            html += "<h4>技术难度细分</h4>"
            html += "<table border=\"1\" cellpadding=\"5\" cellspacing=\"0\" style=\"border-collapse: collapse;\">"
            html += "<tr><th><b>项目</b></th><th><b>分数</b></th></tr>"

            tech = breakdown['technical']
            for key in ['code_volume', 'subsystem_criticality', 'cross_subsystem']:
                if key in tech:
                    name = TECHNICAL_SCORE_TRANSLATIONS.get(key, key)
                    html += f"<tr><td>{name}</td><td>{tech[key]}</td></tr>"

            if 'details' in tech:
                html += f"<tr><td><b>说明</b></td><td>{tech['details']}</td></tr>"

            html += "</table><br>"

        # 影响力评分细分
        if 'impact' in breakdown:
            html += "<h4>影响力细分</h4>"
            html += "<table border=\"1\" cellpadding=\"5\" cellspacing=\"0\" style=\"border-collapse: collapse;\">"
            html += "<tr><th><b>项目</b></th><th><b>分数</b></th></tr>"

            impact = breakdown['impact']
            for key in ['category_base', 'stable_lts', 'user_impact', 'novelty']:
                if key in impact:
                    name = IMPACT_SCORE_TRANSLATIONS.get(key, key)
                    html += f"<tr><td>{name}</td><td>{impact[key]}</td></tr>"

            if 'details' in impact:
                html += f"<tr><td><b>说明</b></td><td>{impact['details']}</td></tr>"

            html += "</table><br>"

        # 质量评分细分
        if 'quality' in breakdown:
            html += "<h4>代码质量细分</h4>"
            html += "<table border=\"1\" cellpadding=\"5\" cellspacing=\"0\" style=\"border-collapse: collapse;\">"
            html += "<tr><th><b>项目</b></th><th><b>分数</b></th></tr>"

            quality = breakdown['quality']
            for key in ['review_chain', 'message_quality', 'testing', 'atomicity']:
                if key in quality:
                    name = QUALITY_SCORE_TRANSLATIONS.get(key, key)
                    html += f"<tr><td>{name}</td><td>{quality[key]}</td></tr>"

            if 'details' in quality:
                html += f"<tr><td><b>说明</b></td><td>{quality['details']}</td></tr>"

            html += "</table><br>"

        # 社区评分细分
        if 'community' in breakdown:
            html += "<h4>社区贡献细分</h4>"
            html += "<table border=\"1\" cellpadding=\"5\" cellspacing=\"0\" style=\"border-collapse: collapse;\">"
            html += "<tr><th><b>项目</b></th><th><b>分数</b></th></tr>"

            community = breakdown['community']
            for key in ['cross_org', 'maintainer', 'response']:
                if key in community:
                    name = COMMUNITY_SCORE_TRANSLATIONS.get(key, key)
                    html += f"<tr><td>{name}</td><td>{community[key]}</td></tr>"

            if 'details' in community:
                html += f"<tr><td><b>说明</b></td><td>{community['details']}</td></tr>"

            html += "</table><br>"

        # 评分理由
        if 'score_justification' in commit:
            html += f"<h4>评分理由</h4>"
            html += f"<p>{commit.get('score_justification', '')}</p>"

        return html

    def create_category_tab(self) -> QWidget:
        """创建分类信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout()

        browser = QTextBrowser()
        html = self._generate_category_html()
        browser.setHtml(html)

        layout.addWidget(browser)
        widget.setLayout(layout)
        return widget

    def _generate_category_html(self) -> str:
        """生成分类信息HTML"""
        commit = self.commit_data

        html = "<h2>分类信息</h2>"

        # 主分类
        primary = commit.get('primary_category', 'N/A')
        primary_translated = translate_category(primary)
        group = get_category_for_group(primary)

        html += f"<h3>主分类: {primary_translated} ({primary})</h3>"
        html += f"<p><b>所属分组:</b> {group}</p>"

        # 次要分类
        secondary = commit.get('secondary_categories', [])
        if secondary:
            html += "<h4>次要分类:</h4>"
            html += "<ul>"
            for sec in secondary:
                sec_translated = translate_category(sec)
                sec_group = get_category_for_group(sec)
                html += f"<li>{sec_translated} ({sec}) - {sec_group}</li>"
            html += "</ul>"

        return html


class CodeSnippetDialog(QDialog):
    """代码片段对话框"""

    def __init__(self, commit_data: Dict[str, Any], parent=None, kernel_repo_path: str = "linux-kernel"):
        super().__init__(parent)
        self.commit_data = commit_data
        self.kernel_repo_path = kernel_repo_path
        self.showing_full_diff = False
        self.setWindowTitle(f"{get_ui_text('code_snippet')} - {commit_data.get('short_hash', '')}")
        self.setMinimumSize(1100, 750)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 标题
        title = QLabel(f"<h3>{self.commit_data.get('subject', 'N/A')}</h3>")
        title.setWordWrap(True)
        layout.addWidget(title)

        # 创建文本文档和代码浏览器
        self.document = QTextDocument()
        self.document.setDefaultFont(QFont("Consolas", 10))

        self.code_browser = QTextBrowser()
        self.code_browser.setDocument(self.document)
        self.code_browser.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)

        # 添加 diff 语法高亮
        self.highlighter = DiffHighlighter(self.document)

        layout.addWidget(self.code_browser)

        # 显示初始内容
        self._load_initial_content()

        # 按钮区域
        btn_layout = QHBoxLayout()

        # 切换完整diff按钮
        self.toggle_diff_btn = QPushButton("📄 显示完整变更")
        self.toggle_diff_btn.clicked.connect(self.toggle_full_diff)
        btn_layout.addWidget(self.toggle_diff_btn)

        btn_layout.addStretch()

        # 打开链接按钮
        if 'link' in self.commit_data:
            link_btn = QPushButton(get_ui_text('open_link'))
            link_btn.clicked.connect(self.open_link)
            btn_layout.addWidget(link_btn)

        # 关闭按钮
        close_btn = QPushButton(get_ui_text('close'))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _load_initial_content(self):
        """加载初始内容"""
        snippet = self.commit_data.get('code_snippet', '无代码片段')

        # 检查是否有完整代码变更
        files_changed = self.commit_data.get('files_changed', 0)
        if files_changed > 1:
            info = f"\n{'='*60}\n⚠️ 该提交修改了 {files_changed} 个文件\n下面只显示 AI 提取的代码片段\n点击「显示完整变更」查看所有文件的 diff\n{'='*60}\n\n"
            self.document.setPlainText(info + snippet)
        else:
            self.document.setPlainText(snippet)

    def toggle_full_diff(self):
        """切换显示完整 diff"""
        if not self.showing_full_diff:
            # 加载完整 diff
            self._load_full_diff()
            self.toggle_diff_btn.setText("📋 显示摘要")
            self.showing_full_diff = True
        else:
            # 显示摘要
            self._load_initial_content()
            self.toggle_diff_btn.setText("📄 显示完整变更")
            self.showing_full_diff = False

    def _load_full_diff(self):
        """从本地仓库加载完整 diff"""
        commit_hash = self.commit_data.get('commit_hash', '')
        if not commit_hash:
            self.document.setPlainText("❌ 无法获取完整代码：未找到 commit hash")
            return

        # 检查仓库是否存在 - 使用当前工作目录
        import os
        repo_path = os.path.join(os.getcwd(), self.kernel_repo_path)

        # 调试信息：显示路径
        print(f"正在查找仓库: {repo_path}")
        print(f"仓库存在: {os.path.exists(repo_path)}")

        if not os.path.exists(repo_path):
            self.document.setPlainText(f"❌ 仓库不存在: {repo_path}\n\n请确保 linux-kernel 子模块已初始化\n\n当前目录: {os.getcwd()}")
            return

        # 显示加载提示
        self.document.setPlainText("⏳ 正在加载完整代码变更...")

        # 使用 QTimer 延迟加载，避免阻塞 UI
        QTimer.singleShot(100, lambda: self._fetch_full_diff(repo_path, commit_hash))

    def _fetch_full_diff(self, repo_path: str, commit_hash: str):
        """获取完整 diff"""
        import subprocess
        try:
            print(f"正在执行: git show {commit_hash}")
            print(f"工作目录: {repo_path}")

            result = subprocess.run(
                ['git', 'show', commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=15,
                encoding='utf-8',
                errors='replace'
            )

            print(f"返回码: {result.returncode}")

            if result.returncode == 0:
                full_diff = result.stdout
                # 添加头部信息
                header = f"📄 完整代码变更 (commit: {commit_hash})\n{'='*60}\n\n"
                self.document.setPlainText(header + full_diff)
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                print(f"Git 错误: {error_msg}")
                self.document.setPlainText(f"❌ 获取完整代码失败:\n{error_msg}\n\n仓库路径: {repo_path}\nCommit: {commit_hash}")
        except subprocess.TimeoutExpired:
            self.document.setPlainText("❌ 获取完整代码超时，请稍后重试")
        except Exception as e:
            print(f"异常: {e}")
            self.document.setPlainText(f"❌ 获取完整代码时出错:\n{str(e)}\n\n仓库路径: {repo_path}")

    def open_link(self):
        """打开提交链接"""
        link = self.commit_data.get('link', '')
        if link:
            QDesktopServices.openUrl(QUrl(link))


class StatsChart(QWidget):
    """统计图表组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 进一步增大图表尺寸
        self.figure = Figure(figsize=(16, 12), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        self.data_loader = None  # 将由主窗口设置

    def set_data_loader(self, data_loader: DataLoader):
        """设置数据加载器引用"""
        self.data_loader = data_loader

    def update_charts(self, companies: List[CompanyData], selected_company: Optional[str] = None):
        """更新图表"""
        self.figure.clear()

        if not companies:
            return

        # 使用更宽松的间距布局 - 2x2网格
        gs = self.figure.add_gridspec(2, 2, hspace=0.40, wspace=0.35,
                                      left=0.10, right=0.96, top=0.93, bottom=0.08)

        # 1. 平均分柱状图 (左上)
        ax1 = self.figure.add_subplot(gs[0, 0])
        self._plot_avg_scores(ax1, companies, selected_company)

        # 2. 总评分柱状图 (右上)
        ax2 = self.figure.add_subplot(gs[0, 1])
        self._plot_total_scores(ax2, companies, selected_company)

        # 3. 分类分布饼图 (左下)
        ax3 = self.figure.add_subplot(gs[1, 0])
        self._plot_category_distribution(ax3, selected_company)

        # 4. 提交数量柱状图 (右下)
        ax4 = self.figure.add_subplot(gs[1, 1])
        self._plot_commit_counts(ax4, companies, selected_company)

        self.canvas.draw()

    def _plot_avg_scores(self, ax, companies: List[CompanyData], selected_company: Optional[str]):
        """绘制平均分柱状图"""
        # 取前10家公司（减少数量以避免拥挤）
        sorted_companies = sorted(companies, key=lambda x: x.avg_score, reverse=True)[:10]

        names = [translate_company_name(c.name) for c in sorted_companies]
        scores = [c.avg_score for c in sorted_companies]

        colors = ['#ff6b6b' if c.name == selected_company else '#4ecdc4' for c in sorted_companies]

        bars = ax.bar(names, scores, color=colors, width=0.6)
        ax.set_title(get_ui_text('avg_score_chart'), fontsize=13, fontweight='bold', pad=12)
        ax.set_ylabel('平均分', fontsize=11)
        ax.set_xlabel('公司', fontsize=11)
        ax.tick_params(axis='x', rotation=30, labelsize=9)
        ax.tick_params(axis='y', labelsize=9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # 添加数值标签
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{score:.1f}', ha='center', va='bottom', fontsize=8)

    def _plot_total_scores(self, ax, companies: List[CompanyData], selected_company: Optional[str]):
        """绘制总评分柱状图"""
        sorted_companies = sorted(companies, key=lambda x: x.total_score, reverse=True)[:10]

        names = [translate_company_name(c.name) for c in sorted_companies]
        scores = [c.total_score for c in sorted_companies]

        colors = ['#ff6b6b' if c.name == selected_company else '#45b7d1' for c in sorted_companies]

        bars = ax.bar(names, scores, color=colors, width=0.6)
        ax.set_title(get_ui_text('total_score_chart'), fontsize=13, fontweight='bold', pad=12)
        ax.set_ylabel('总评分', fontsize=11)
        ax.set_xlabel('公司', fontsize=11)
        ax.tick_params(axis='x', rotation=30, labelsize=9)
        ax.tick_params(axis='y', labelsize=9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(score)}', ha='center', va='bottom', fontsize=8)

    def _plot_category_distribution(self, ax, selected_company: Optional[str]):
        """绘制分类分布饼图"""
        if not selected_company:
            ax.text(0.5, 0.5, '请选择公司', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            return

        # 从数据加载器中获取该公司数据
        if self.data_loader and selected_company in self.data_loader.companies:
            company_data = self.data_loader.companies.get(selected_company)
            if company_data and company_data.categories:
                # 按分类组聚合
                group_counts = {}
                for cat, count in company_data.categories.items():
                    group = get_category_for_group(cat)
                    group_counts[group] = group_counts.get(group, 0) + count

                if group_counts:
                    labels = list(group_counts.keys())
                    sizes = list(group_counts.values())

                    # 使用更好的颜色方案，增加饼图之间的间距
                    colors = plt.cm.Set2(range(len(labels)))
                    explode = tuple([0.02] * len(labels))  # 添加小的爆炸效果分离扇区
                    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                                       colors=colors, startangle=90,
                                                       pctdistance=0.80, labeldistance=1.15,
                                                       explode=explode, textprops={'fontsize': 10})
                    # 设置百分比文字样式
                    for autotext in autotexts:
                        autotext.set_color('black')
                        autotext.set_fontsize(9)
                        autotext.set_fontweight('bold')
                    # 设置标签文字样式
                    for text in texts:
                        text.set_fontsize(10)

                    # 缩短标题 - 使用中文公司名
                    chinese_name = translate_company_name(selected_company)
                    title = f"{get_ui_text('category_distribution')}"
                    if len(chinese_name) > 8:
                        title = f"{chinese_name[:8]}... - {title}"
                    else:
                        title = f"{chinese_name} - {title}"
                    ax.set_title(title, fontsize=12, fontweight='bold', pad=12)
                else:
                    ax.text(0.5, 0.5, '无分类数据', ha='center', va='center',
                           transform=ax.transAxes, fontsize=12)
            else:
                ax.text(0.5, 0.5, '无分类数据', ha='center', va='center',
                       transform=ax.transAxes, fontsize=12)
        else:
            ax.text(0.5, 0.5, '请选择公司', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)

    def _plot_commit_counts(self, ax, companies: List[CompanyData], selected_company: Optional[str]):
        """绘制提交数量柱状图"""
        sorted_companies = sorted(companies, key=lambda x: x.commit_count, reverse=True)[:10]

        names = [translate_company_name(c.name) for c in sorted_companies]
        counts = [c.commit_count for c in sorted_companies]

        colors = ['#ff6b6b' if c.name == selected_company else '#96ceb4' for c in sorted_companies]

        bars = ax.bar(names, counts, color=colors, width=0.6)
        ax.set_title(get_ui_text('commit_count'), fontsize=13, fontweight='bold', pad=12)
        ax.set_ylabel('提交数量', fontsize=11)
        ax.set_xlabel('公司', fontsize=11)
        ax.tick_params(axis='x', rotation=30, labelsize=9)
        ax.tick_params(axis='y', labelsize=9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{count}', ha='center', va='bottom', fontsize=8)


class MainWindow(QMainWindow):
    """主窗口"""

    _instance = None

    def __init__(self):
        super().__init__()
        MainWindow._instance = self

        self.data_loader = DataLoader()
        self.current_company: Optional[str] = None

        # 分页相关变量
        self.current_commits_df = None  # 当前公司的所有提交数据
        self.current_page = 0
        self.page_size = 100  # 每页显示100条

        self.setup_ui()
        self.load_data()

    @staticmethod
    def get_instance():
        """获取主窗口实例"""
        return MainWindow._instance

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(get_ui_text('app_title'))
        self.setMinimumSize(1600, 1000)
        self.resize(1600, 1000)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 顶部搜索栏
        top_layout = QHBoxLayout()

        search_label = QLabel("🔍 搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(get_ui_text('filter_placeholder'))
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self.on_search_changed)

        refresh_btn = QPushButton(get_ui_text('refresh_data'))
        refresh_btn.clicked.connect(self.refresh_data)

        top_layout.addWidget(search_label)
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(refresh_btn)
        top_layout.addStretch()

        main_layout.addLayout(top_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧：公司排名表格
        left_widget = self.create_company_ranking_widget()
        splitter.addWidget(left_widget)

        # 右侧：统计图表和提交详情
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([400, 1200])  # 设置初始宽度比例

        main_layout.addWidget(splitter)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        central_widget.setLayout(main_layout)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu(get_ui_text('file_menu'))

        refresh_action = QAction(get_ui_text('refresh_data'), self)
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)

        exit_action = QAction(get_ui_text('exit'), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def create_company_ranking_widget(self) -> QWidget:
        """创建公司排名组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        title = QLabel(f"<h2 style='color: #2c3e50;'>🏆 {get_ui_text('company_ranking')}</h2>")
        layout.addWidget(title)

        # 排序选择
        sort_layout = QHBoxLayout()
        sort_label = QLabel("📊 排序方式:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            get_ui_text('total_score'),
            get_ui_text('avg_score'),
            get_ui_text('commit_count')
        ])
        self.sort_combo.currentIndexChanged.connect(self.update_company_table)
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # 公司表格
        self.company_table = QTableWidget()
        self.company_table.setColumnCount(4)
        self.company_table.setHorizontalHeaderLabels([
            get_ui_text('company_name'),
            get_ui_text('commit_count'),
            get_ui_text('total_score'),
            get_ui_text('avg_score')
        ])
        self.company_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.company_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.company_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.company_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.company_table.setAlternatingRowColors(True)
        self.company_table.cellClicked.connect(self.on_company_selected)

        # 设置表格样式
        self.company_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 8px;
                font-weight: bold;
                border: 1px solid #bdc3c7;
            }
        """)

        layout.addWidget(self.company_table)

        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        self.max_score_label = QLabel()
        self.min_score_label = QLabel()
        self.max_score_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.min_score_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        stats_layout.addWidget(self.max_score_label)
        stats_layout.addWidget(self.min_score_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        widget.setLayout(layout)
        return widget

    def create_right_panel(self) -> QWidget:
        """创建右侧面板 - 使用标签页分离不同视图"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # 创建标签页
        self.tabs = QTabWidget()

        # 标签页1: 统计图表
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(10, 10, 10, 10)
        self.chart_widget = StatsChart()
        self.chart_widget.set_data_loader(self.data_loader)
        chart_layout.addWidget(self.chart_widget)
        chart_tab.setLayout(chart_layout)
        self.tabs.addTab(chart_tab, "📊 统计图表")

        # 标签页2: 提交详情
        commit_tab = QWidget()
        commit_layout = QVBoxLayout()
        commit_layout.setContentsMargins(10, 10, 10, 10)

        # 添加说明标签
        info_label = QLabel("💡 提示：右键点击提交行可查看代码片段和详细分析")
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        commit_layout.addWidget(info_label)

        self.commit_table = QTableWidget()
        self.commit_table.setColumnCount(6)
        self.commit_table.setHorizontalHeaderLabels([
            get_ui_text('commit_hash'),
            get_ui_text('date'),
            get_ui_text('author'),
            get_ui_text('category'),
            get_ui_text('score'),
            get_ui_text('subject')
        ])

        # 启用排序功能
        self.commit_table.setSortingEnabled(False)  # 我们自己实现排序，因为需要处理分页数据

        # 设置表格属性
        header = self.commit_table.horizontalHeader()
        header.setSectionsClickable(True)  # 允许点击表头
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Hash
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Author
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Category
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Score
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Subject

        # 连接表头点击事件
        header.sectionClicked.connect(self.on_commit_header_clicked)

        # 存储当前提交数据（用于排序）
        self.current_commit_data = []  # 当前显示的所有提交数据
        self.commit_sort_column = None    # 当前排序列
        self.commit_sort_order = Qt.SortOrder.AscendingOrder  # 当前排序方向

        self.commit_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.commit_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.commit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.commit_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.commit_table.setAlternatingRowColors(True)
        self.commit_table.customContextMenuRequested.connect(self.show_commit_context_menu)
        self.commit_table.cellEntered.connect(self.on_commit_hover)

        commit_layout.addWidget(self.commit_table)

        # 分页控制栏
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)

        # 统计信息
        self.commit_stats_label = QLabel("共 0 条提交")
        self.commit_stats_label.setStyleSheet("color: #666; font-size: 11px;")
        pagination_layout.addWidget(self.commit_stats_label)

        pagination_layout.addStretch()

        # 加载更多按钮
        self.load_more_btn = QPushButton("⬇️ 加载更多")
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.clicked.connect(self.load_more_commits)
        pagination_layout.addWidget(self.load_more_btn)

        # 翻页按钮
        self.prev_page_btn = QPushButton("⬅️ 上一页")
        self.prev_page_btn.setEnabled(False)
        self.prev_page_btn.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_page_btn)

        self.next_page_btn = QPushButton("➡️ 下一页")
        self.next_page_btn.setEnabled(False)
        self.next_page_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_page_btn)

        commit_layout.addLayout(pagination_layout)
        commit_tab.setLayout(commit_layout)
        self.tabs.addTab(commit_tab, "📋 提交详情")

        layout.addWidget(self.tabs)

        widget.setLayout(layout)
        return widget

    def load_data(self):
        """加载数据"""
        self.status_bar.showMessage(get_ui_text('loading_data'))

        # 查找数据文件
        if not self.data_loader.find_data_files():
            QMessageBox.warning(self, get_ui_text('error_loading'),
                              "未找到数据文件，请确保 data 目录包含 chinese_companies_*.jsonl 文件")
            self.status_bar.showMessage(get_ui_text('no_data'))
            return

        # 加载数据
        self.data_loader.load_commits()
        self.data_loader.load_summaries()

        # 更新界面
        self.update_company_table()
        self.update_charts()

        self.status_bar.showMessage(
            f"{get_ui_text('data_loaded')} - {len(self.data_loader.companies)} {get_ui_text('companies_loaded')}, "
            f"{len(self.data_loader.commits_df) if self.data_loader.commits_df is not None else 0} {get_ui_text('commits_loaded')}"
        )

    def refresh_data(self):
        """刷新数据"""
        self.data_loader = DataLoader()
        self.chart_widget.set_data_loader(self.data_loader)
        self.load_data()

    def update_company_table(self):
        """更新公司表格"""
        companies = list(self.data_loader.companies.values())

        # 根据选择的排序方式排序
        sort_by = self.sort_combo.currentText()
        if sort_by == get_ui_text('total_score'):
            companies.sort(key=lambda x: x.total_score, reverse=True)
        elif sort_by == get_ui_text('avg_score'):
            companies.sort(key=lambda x: x.avg_score, reverse=True)
        elif sort_by == get_ui_text('commit_count'):
            companies.sort(key=lambda x: x.commit_count, reverse=True)

        # 应用搜索过滤（支持中英文搜索）
        search_text = self.search_input.text().lower()
        if search_text:
            filtered_companies = []
            for c in companies:
                # 检查英文名
                if search_text in c.name.lower():
                    filtered_companies.append(c)
                # 检查中文名
                elif search_text in translate_company_name(c.name).lower():
                    filtered_companies.append(c)
            companies = filtered_companies

        # 更新表格
        self.company_table.setRowCount(len(companies))

        for row, company in enumerate(companies):
            # 使用中文公司名，英文保存在UserRole中用于搜索和查找
            chinese_name = translate_company_name(company.name)
            name_item = QTableWidgetItem(chinese_name)
            name_item.setData(Qt.ItemDataRole.UserRole, company.name)  # 保存英文名
            name_item.setToolTip(company.name)  # 鼠标悬停显示英文名
            self.company_table.setItem(row, 0, name_item)

            self.company_table.setItem(row, 1, QTableWidgetItem(str(company.commit_count)))
            self.company_table.setItem(row, 2, QTableWidgetItem(str(company.total_score)))
            self.company_table.setItem(row, 3, QTableWidgetItem(f"{company.avg_score:.2f}"))

        # 更新统计标签
        if companies:
            max_company = max(companies, key=lambda x: x.max_score)
            min_company = min(companies, key=lambda x: x.min_score if x.min_score != float('inf') else 999999)
            max_chinese = translate_company_name(max_company.name)
            min_chinese = translate_company_name(min_company.name)
            self.max_score_label.setText(
                f"{get_ui_text('max_score')}: {max_company.max_score} ({max_chinese})"
            )
            self.min_score_label.setText(
                f"{get_ui_text('min_score')}: {min_company.min_score} ({min_chinese})"
            )

        # 更新图表
        self.update_charts(companies)

    def update_charts(self, companies=None):
        """更新图表"""
        if companies is None:
            companies = list(self.data_loader.companies.values())
        self.chart_widget.update_charts(companies, self.current_company)

    def on_search_changed(self, text):
        """搜索文本变化"""
        self.update_company_table()

    def on_company_selected(self, row, column):
        """公司被选中"""
        name_item = self.company_table.item(row, 0)
        # 从UserRole中获取英文名
        company_name = name_item.data(Qt.ItemDataRole.UserRole)
        self.current_company = company_name

        # 更新提交详情表格
        self.update_commit_table(company_name)

        # 更新图表
        self.update_charts()

    def update_commit_table(self, company_name: str):
        """更新提交详情表格 - 使用分页加载"""
        # 获取公司所有提交数据
        commits_df = self.data_loader.get_commits_by_company(company_name)

        if commits_df.empty:
            self.commit_table.setRowCount(0)
            self.commit_stats_label.setText("共 0 条提交")
            self.load_more_btn.setEnabled(False)
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            return

        # 按日期降序排序（初始排序）
        self.current_commits_df = commits_df.sort_values('author_date', ascending=False)
        self.current_page = 0

        # 重置排序状态
        self.commit_sort_column = None
        self.commit_sort_order = Qt.SortOrder.AscendingOrder

        # 清除表头排序指示器
        header = self.commit_table.horizontalHeader()
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)  # -1 表示清除所有排序指示器

        # 更新统计信息
        total_count = len(self.current_commits_df)
        self.commit_stats_label.setText(f"共 {total_count} 条提交，显示 {min(self.page_size, total_count)} 条")

        # 只加载第一页数据
        self._load_commits_page(0)

        # 更新分页按钮状态
        self._update_pagination_buttons()

    def _load_commits_page(self, page: int):
        """加载指定页的数据"""
        if self.current_commits_df is None:
            return

        start_idx = page * self.page_size
        end_idx = start_idx + self.page_size

        # 获取当前页数据
        page_df = self.current_commits_df.iloc[start_idx:end_idx]

        # 清空表格并设置行数
        self.commit_table.setRowCount(len(page_df))

        # 存储当前页的提交数据（用于排序）
        self.current_commit_data = []

        for row_idx, (_, commit) in enumerate(page_df.iterrows()):
            # 转换为字典存储
            commit_dict = commit.to_dict() if hasattr(commit, 'to_dict') else dict(commit)
            self.current_commit_data.append(commit_dict)

            hash_item = QTableWidgetItem(commit.get('short_hash', ''))
            hash_item.setData(Qt.ItemDataRole.UserRole, commit.get('commit_hash', ''))
            self.commit_table.setItem(row_idx, 0, hash_item)

            # 日期
            date_str = ''
            if pd.notna(commit.get('author_date')):
                date = commit['author_date']
                date_str = date.strftime('%Y-%m-%d')
            self.commit_table.setItem(row_idx, 1, QTableWidgetItem(date_str))

            # 作者
            author = commit.get('author_name', '')
            self.commit_table.setItem(row_idx, 2, QTableWidgetItem(author))

            # 分类
            primary = commit.get('primary_category', '')
            primary_translated = translate_category(primary)
            self.commit_table.setItem(row_idx, 3, QTableWidgetItem(primary_translated))

            # 评分
            self.commit_table.setItem(row_idx, 4, QTableWidgetItem(str(commit.get('score_total', 0))))

            # 主题
            subject = commit.get('subject', '')
            self.commit_table.setItem(row_idx, 5, QTableWidgetItem(subject))

            # 存储完整提交数据
            self.commit_table.item(row_idx, 0).setData(Qt.ItemDataRole.UserRole + 1, commit_dict)

    def _update_pagination_buttons(self):
        """更新分页按钮状态"""
        if self.current_commits_df is None or len(self.current_commits_df) == 0:
            self.load_more_btn.setEnabled(False)
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            return

        total_count = len(self.current_commits_df)
        current_loaded = (self.current_page + 1) * self.page_size

        # 更新统计信息
        self.commit_stats_label.setText(
            f"共 {total_count} 条提交，显示 {min(current_loaded, total_count)} 条"
        )

        # 更新按钮状态
        self.load_more_btn.setEnabled(current_loaded < total_count)
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(current_loaded < total_count)

    def load_more_commits(self):
        """加载更多提交"""
        if self.current_commits_df is None:
            return

        self.current_page += 1
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size

        if start_idx >= len(self.current_commits_df):
            return

        # 追加新数据到表格
        current_row_count = self.commit_table.rowCount()
        page_df = self.current_commits_df.iloc[start_idx:end_idx]

        # 设置新行数
        self.commit_table.setRowCount(current_row_count + len(page_df))

        for row_idx, (_, commit) in enumerate(page_df.iterrows()):
            actual_row = current_row_count + row_idx

            # 转换为字典存储
            commit_dict = commit.to_dict() if hasattr(commit, 'to_dict') else dict(commit)
            self.current_commit_data.append(commit_dict)

            hash_item = QTableWidgetItem(commit.get('short_hash', ''))
            hash_item.setData(Qt.ItemDataRole.UserRole, commit.get('commit_hash', ''))
            self.commit_table.setItem(actual_row, 0, hash_item)

            # 日期
            date_str = ''
            if pd.notna(commit.get('author_date')):
                date = commit['author_date']
                date_str = date.strftime('%Y-%m-%d')
            self.commit_table.setItem(actual_row, 1, QTableWidgetItem(date_str))

            # 作者
            author = commit.get('author_name', '')
            self.commit_table.setItem(actual_row, 2, QTableWidgetItem(author))

            # 分类
            primary = commit.get('primary_category', '')
            primary_translated = translate_category(primary)
            self.commit_table.setItem(actual_row, 3, QTableWidgetItem(primary_translated))

            # 评分
            self.commit_table.setItem(actual_row, 4, QTableWidgetItem(str(commit.get('score_total', 0))))

            # 主题
            subject = commit.get('subject', '')
            self.commit_table.setItem(actual_row, 5, QTableWidgetItem(subject))

            # 存储完整提交数据
            self.commit_table.item(actual_row, 0).setData(Qt.ItemDataRole.UserRole + 1, commit.to_dict())

        self._update_pagination_buttons()

    def next_page(self):
        """下一页"""
        self.load_more_commits()

    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self._load_commits_page(self.current_page)
            self._update_pagination_buttons()

    def on_commit_hover(self, row, column):
        """提交行悬停"""
        if column == 0:  # 只在哈希列显示
            item = self.commit_table.item(row, column)
            if item:
                full_hash = item.data(Qt.ItemDataRole.UserRole)
                self.commit_table.setToolTip(full_hash)

    def on_commit_header_clicked(self, column: int):
        """提交详情表头点击 - 排序"""
        # 切换排序方向
        if self.commit_sort_column == column:
            # 同一列，切换方向
            self.commit_sort_order = Qt.SortOrder.DescendingOrder if self.commit_sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            # 不同列，默认升序
            self.commit_sort_column = column
            self.commit_sort_order = Qt.SortOrder.AscendingOrder

        # 执行排序
        self._sort_and_display_commits()

        # 更新表头排序指示器
        self._update_header_sort_indicator()

    def _sort_and_display_commits(self):
        """排序并显示提交数据"""
        if self.current_commits_df is None or len(self.current_commits_df) == 0:
            return

        # 根据列名获取排序键
        sort_keys = {
            0: 'short_hash',      # Hash
            1: 'author_date',      # Date
            2: 'author_name',      # Author
            3: 'primary_category', # Category
            4: 'score_total',     # Score
            5: 'subject'          # Subject
        }

        sort_key = sort_keys.get(self.commit_sort_column, 'author_date')

        # 排序
        ascending = self.commit_sort_order == Qt.SortOrder.AscendingOrder

        # 对于日期，确保是 datetime 类型
        if sort_key == 'author_date':
            self.current_commits_df = self.current_commits_df.copy()
            self.current_commits_df[sort_key] = pd.to_datetime(self.current_commits_df[sort_key], errors='coerce')

        # 对整个数据集进行排序
        self.current_commits_df = self.current_commits_df.sort_values(by=sort_key, ascending=ascending)

        # 重置到第一页并重新加载
        self.current_page = 0
        self._load_commits_page(0)

        # 更新分页按钮状态
        self._update_pagination_buttons()

    def _update_header_sort_indicator(self):
        """更新表头排序指示器"""
        header = self.commit_table.horizontalHeader()

        # 设置排序指示器
        if self.commit_sort_column is not None:
            header.setSortIndicator(self.commit_sort_column, self.commit_sort_order)

    def show_commit_context_menu(self, pos):
        """显示提交右键菜单"""
        item = self.commit_table.itemAt(pos)
        if not item:
            return

        row = item.row()
        commit_item = self.commit_table.item(row, 0)
        commit_data = commit_item.data(Qt.ItemDataRole.UserRole + 1)

        menu = QMenu(self)

        view_code_action = QAction(get_ui_text('view_code'), self)
        view_code_action.triggered.connect(lambda: self.view_code_snippet(commit_data))
        menu.addAction(view_code_action)

        view_analysis_action = QAction(get_ui_text('view_analysis'), self)
        view_analysis_action.triggered.connect(lambda: self.view_analysis_result(commit_data))
        menu.addAction(view_analysis_action)

        if commit_data.get('link'):
            open_link_action = QAction(get_ui_text('open_link'), self)
            open_link_action.triggered.connect(lambda: self.open_commit_link(commit_data['link']))
            menu.addAction(open_link_action)

        copy_hash_action = QAction(get_ui_text('copy_hash'), self)
        copy_hash_action.triggered.connect(lambda: self.copy_commit_hash(commit_data.get('commit_hash', '')))
        menu.addAction(copy_hash_action)

        menu.exec(self.commit_table.mapToGlobal(pos))

    def view_code_snippet(self, commit_data: Dict):
        """查看代码片段"""
        dialog = CodeSnippetDialog(commit_data, self)
        dialog.exec()

    def view_analysis_result(self, commit_data: Dict):
        """查看分析结果"""
        dialog = CommitDetailDialog(commit_data, self)
        dialog.exec()

    def open_commit_link(self, link: str):
        """打开提交链接"""
        QDesktopServices.openUrl(QUrl(link))

    def copy_commit_hash(self, hash_str: str):
        """复制提交哈希"""
        clipboard = QApplication.clipboard()
        clipboard.setText(hash_str)
        self.status_bar.showMessage(f"已复制: {hash_str}", 3000)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置全局样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f6fa;
        }
        QWidget {
            font-family: "Microsoft YaHei", "SimHei", Arial;
            font-size: 11px;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #21618c;
        }
        QLineEdit {
            padding: 6px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: white;
        }
        QLineEdit:focus {
            border: 1px solid #3498db;
        }
        QComboBox {
            padding: 6px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: white;
        }
        QComboBox::drop-down {
            border: none;
        }
        QTabWidget::pane {
            border: 1px solid #bdc3c7;
            background-color: white;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #ecf0f1;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #3498db;
        }
        QTabBar::tab:hover {
            background-color: #d5dbdb;
        }
        QLabel {
            color: #2c3e50;
        }
        QSplitter::handle {
            background-color: #bdc3c7;
            width: 2px;
        }
        QSplitter::handle:hover {
            background-color: #3498db;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
