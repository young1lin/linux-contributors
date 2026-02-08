# -*- coding: utf-8 -*-
"""
中英文翻译映射模块
Linux 内核中国公司贡献分析工具
"""


# 分类代码翻译
CATEGORY_TRANSLATIONS = {
    # 安全相关
    "SEC-CVE": "CVE安全修复",
    "SEC-VULN": "漏洞修复",
    "SEC-HARDEN": "安全加固",
    "SEC-ACCESS": "访问控制",
    "SEC-CRYPTO": "加密相关",

    # Bug修复
    "BUG-CRASH": "崩溃修复",
    "BUG-CORRUPT": "数据损坏修复",
    "BUG-MEMLEAK": "内存泄漏修复",
    "BUG-DEADLOCK": "死锁修复",
    "BUG-RACE": "竞态条件修复",
    "BUG-REGRESSION": "回归修复",
    "BUG-LOGIC": "逻辑错误修复",
    "BUG-RESOURCE": "资源泄漏修复",
    "BUG-COMPAT": "兼容性修复",
    "BUG-PERF-REG": "性能回归修复",
    "BUG-FUNC": "函数错误修复",

    # 新功能
    "FEAT-DRIVER": "驱动程序新功能",
    "FEAT-SUBSYS": "子系统新功能",
    "FEAT-HW": "硬件支持",
    "FEAT-API": "API新功能",
    "FEAT-FUNC": "功能增强",
    "FEAT-PERF": "性能优化",
    "FEAT-POWER": "电源管理",
    "FEAT-SCALE": "可扩展性",
    "FEAT-TEST": "测试功能",
    "FEAT-TRACE": "跟踪功能",
    "FEAT-POWER": "电源管理",

    # 维护
    "MAINT-REFACTOR": "重构",
    "MAINT-SIMPLIFY": "代码简化",
    "MAINT-CLEANUP": "清理",
    "MAINT-API-MIG": "API迁移",
    "MAINT-DEPR": "弃用处理",
    "MAINT-NAMING": "命名规范",
    "MAINT-WARN": "警告修复",
    "MAINT-DUP": "重复代码消除",

    # 微不足道
    "TRIV-TYPO": "拼写错误修复",
    "TRIV-WHITESPACE": "空格调整",
    "TRIV-COMMENT": "注释更新",
    "TRIV-INCLUDE": "头文件调整",
    "TRIV-COPYRIGHT": "版权更新",

    # 文档
    "DOC-KERNEL": "内核文档",
    "DOC-API": "API文档",
    "DOC-KCONFIG": "配置文档",
    "DOC-MAINTAINERS": "维护者文档",
    "DOC-CHANGELOG": "变更日志",

    # 构建
    "BUILD-KCONFIG": "配置更新",
    "BUILD-MAKEFILE": "Makefile更新",
    "BUILD-FIX": "构建修复",
    "BUILD-CI": "CI配置",
    "BUILD-TOOLCHAIN": "工具链",

    # 设备树
    "DT-BINDING": "设备树绑定",
    "DT-SOURCE": "设备树源文件",
    "DT-FIX": "设备树修复",

    # 回传
    "BACK-STABLE": "稳定版本回传",
    "BACK-REVERT": "回退",
    "BACK-MERGE": "合并",

    # 其他
    "FAILED": "分析失败",
}


# 分类分组
CATEGORY_GROUPS = {
    "安全": ["SEC-CVE", "SEC-VULN", "SEC-HARDEN", "SEC-ACCESS", "SEC-CRYPTO"],
    "Bug修复": ["BUG-CRASH", "BUG-CORRUPT", "BUG-MEMLEAK", "BUG-DEADLOCK",
                "BUG-RACE", "BUG-REGRESSION", "BUG-LOGIC", "BUG-RESOURCE",
                "BUG-COMPAT", "BUG-PERF-REG", "BUG-FUNC"],
    "新功能": ["FEAT-DRIVER", "FEAT-SUBSYS", "FEAT-HW", "FEAT-API", "FEAT-FUNC",
               "FEAT-PERF", "FEAT-POWER", "FEAT-SCALE", "FEAT-TEST", "FEAT-TRACE"],
    "维护": ["MAINT-REFACTOR", "MAINT-SIMPLIFY", "MAINT-CLEANUP", "MAINT-API-MIG",
             "MAINT-DEPR", "MAINT-NAMING", "MAINT-WARN", "MAINT-DUP"],
    "微不足道": ["TRIV-TYPO", "TRIV-WHITESPACE", "TRIV-COMMENT", "TRIV-INCLUDE",
                 "TRIV-COPYRIGHT"],
    "文档": ["DOC-KERNEL", "DOC-API", "DOC-KCONFIG", "DOC-MAINTAINERS", "DOC-CHANGELOG"],
    "构建": ["BUILD-KCONFIG", "BUILD-MAKEFILE", "BUILD-FIX", "BUILD-CI", "BUILD-TOOLCHAIN"],
    "设备树": ["DT-BINDING", "DT-SOURCE", "DT-FIX"],
    "回传": ["BACK-STABLE", "BACK-REVERT", "BACK-MERGE"],
    "其他": ["FAILED"],
}


# 评分维度翻译
SCORE_DIMENSION_TRANSLATIONS = {
    "score_total": "总分",
    "score_technical": "技术难度",
    "score_impact": "影响力",
    "score_quality": "代码质量",
    "score_community": "社区贡献",
}


# 技术评分细分
TECHNICAL_SCORE_TRANSLATIONS = {
    "code_volume": "代码量",
    "subsystem_criticality": "子系统关键性",
    "cross_subsystem": "跨子系统",
}


# 影响力评分细分
IMPACT_SCORE_TRANSLATIONS = {
    "category_base": "分类基础分",
    "stable_lts": "稳定/LTS版本",
    "user_impact": "用户影响",
    "novelty": "创新性",
}


# 质量评分细分
QUALITY_SCORE_TRANSLATIONS = {
    "review_chain": "审核链",
    "message_quality": "提交信息质量",
    "testing": "测试覆盖",
    "atomicity": "原子性",
}


# 社区评分细分
COMMUNITY_SCORE_TRANSLATIONS = {
    "cross_org": "跨组织",
    "maintainer": "维护者",
    "response": "响应度",
}


# 子系统层级翻译
SUBSYSTEM_TIER_TRANSLATIONS = {
    1: "最关键 (核心内核)",
    2: "非常关键 (架构核心)",
    3: "关键 (主要工具)",
    4: "重要 (驱动子系统)",
    5: "一般 (辅助功能)",
    6: "轻微 (文档/配置)",
}


# UI文本翻译
UI_TEXT = {
    "app_title": "Linux内核中国公司贡献分析工具",
    "file_menu": "文件",
    "open_data": "打开数据目录",
    "refresh_data": "刷新数据",
    "exit": "退出",
    "view_menu": "查看",
    "help_menu": "帮助",
    "about": "关于",

    # 公司排名表格
    "company_ranking": "公司排名",
    "company_name": "公司名称",
    "commit_count": "提交数量",
    "total_score": "总评分",
    "avg_score": "平均分",
    "max_score": "最高分",
    "min_score": "最低分",

    # 统计图表
    "statistics": "评分统计",
    "avg_score_chart": "各公司平均分",
    "total_score_chart": "各公司总评分",
    "category_distribution": "分类分布",
    "highest_score": "最高分",
    "lowest_score": "最低分",
    "selected_company": "选中公司",

    # 提交详情
    "commit_details": "提交详情",
    "commit_hash": "提交哈希",
    "date": "日期",
    "author": "作者",
    "category": "分类",
    "score": "评分",
    "subject": "主题",

    # 右键菜单
    "view_code": "查看提交代码",
    "view_analysis": "查看分析结果",
    "open_link": "打开链接",
    "copy_hash": "复制哈希",

    # 弹窗标题
    "code_snippet": "代码片段",
    "analysis_result": "分析结果",
    "score_details": "评分详情",
    "close": "关闭",

    # 状态栏
    "loading_data": "正在加载数据...",
    "data_loaded": "数据加载完成",
    "companies_loaded": "家公司",
    "commits_loaded": "条提交记录",
    "filter_placeholder": "搜索公司...",

    # 其他
    "all_categories": "全部分类",
    "all_companies": "全部公司",
    "no_data": "无数据",
    "error_loading": "加载数据时出错",
}


def translate_category(category_code: str) -> str:
    """翻译分类代码"""
    return CATEGORY_TRANSLATIONS.get(category_code, category_code)


def translate_category_group(group_name: str) -> str:
    """翻译分类组名"""
    return group_name  # 已经是中文


def translate_score_dimension(dimension: str) -> str:
    """翻译评分维度"""
    return SCORE_DIMENSION_TRANSLATIONS.get(dimension, dimension)


def translate_subsystem_tier(tier: int) -> str:
    """翻译子系统层级"""
    return SUBSYSTEM_TIER_TRANSLATIONS.get(tier, f"层级 {tier}")


def get_ui_text(key: str) -> str:
    """获取UI文本"""
    return UI_TEXT.get(key, key)


def get_category_for_group(category: str) -> str:
    """获取分类所属的组"""
    for group_name, categories in CATEGORY_GROUPS.items():
        if category in categories:
            return group_name
    return "其他"


# 公司名中英文映射
COMPANY_NAME_TRANSLATIONS = {
    "Huawei": "华为",
    "MediaTek": "联发科",
    "ZTE": "中兴",
    "HiSilicon": "海思",
    "Inspur": "浪潮",
    "Loongson": "龙芯",
    "Baidu": "百度",
    "Lenovo": "联想",
    "Kylin": "麒麟",
    "JD": "京东",
    "Linaro": "Linaro",
    "Tencent": "腾讯",
    "ByteDance": "字节跳动",
    "OPPO": "OPPO",
    "Vivo": "Vivo",
    "Xiaomi": "小米",
    "Alibaba": "阿里",
    "Tencent": "腾讯",
    "Deepin": "深度",
    "UnionTech": "统信",
    "Phytium": "飞腾",
    "Sunway": "申威",
}


def translate_company_name(english_name: str) -> str:
    """翻译公司名称"""
    return COMPANY_NAME_TRANSLATIONS.get(english_name, english_name)
