ALLOWED_WORKFLOW_NODE_TYPES = {
    "userGuide",
    "workflowStart",
    "chatNode",
    "datasetSearchNode",
    "datasetConcatNode",
    "answerNode",
    "classifyQuestion",
    "contentExtract",
    "httpRequest468",
    "code",
    "ifElseNode",
    "variableUpdate",
    "textEditor",
    "readFiles",
    "userSelect",
    "formInput",
    "loop",
    "parallelRun",
    "loopStart",
    "loopEnd",
    "pluginConfig",
    "pluginInput",
    "pluginOutput",
    "pluginModule",
    "appModule",
    "app",
    "tool",
    "toolSet",
    "agent",
    "tools",
}

ALLOWED_CHATCONFIG_KEYS = {
    "welcomeText",
    "variables",
    "autoExecute",
    "questionGuide",
    "ttsConfig",
    "whisperConfig",
    "scheduledTriggerConfig",
    "chatInputGuide",
    "fileSelectConfig",
    "instruction",
}

MIGRATION_MODES = {
    "workflow-only",
    "workflow+workflow-tools",
    "exception-helper-approved",
}

LEGACY_HELPER_MARKERS = {
    "__RAG_HELPER_BASE_URL__",
    "__RAG_HELPER_API_KEY__",
    "/api/rag-helper/",
}

MCP_CONFIG_MARKERS = {
    "mcpTool",
    "mcp-app",
    "mcpToolSet",
}
