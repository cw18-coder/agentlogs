from __future__ import annotations

import datetime as dt
import json
from typing import Any, ClassVar, Mapping

from agentlogs.schema import (
    AgentSessionLogEntry,
)
from agentlogs.schema.types.agent_session_log import (
    AgentSessionLogEntryData,
    Choice,
    CompletionTokensDetails,
    ContentFilterCategory,
    ContentFilterResults,
    ContentPart,
    CopilotAnnotations,
    CopilotBillingMetadata,
    CopilotInfoMessage,
    CopilotUsage,
    CopilotWarningMessage,
    Delta,
    DeltaToolCall,
    ErrorInfo,
    Citation,
    CitationEntry,
    Message,
    MessageToolCall,
    PromptFilterResult,
    PromptTokensDetails,
    TokenDetail,
    ToolTelemetry,
    ToolTelemetryMetrics,
    ToolTelemetryProperties,
    ToolTelemetryRestrictedProperties,
    TruncateResult,
    Usage,
    UsageCopilotUsage,
)
from .exporter import Exporter
from .common import format_session_reference
from ..resources import SessionRef
from ..state import ResourceRecord

class SessionLogExporter(Exporter[AgentSessionLogEntry]):
    resource_type: ClassVar[str] = "session_log"
    expand_relations: ClassVar[list[str]] = ["session_session_log"]

    def get_record_type(self) -> type[AgentSessionLogEntry]:
        return AgentSessionLogEntry

    def format_resource(
        self,
        resource: ResourceRecord,
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]],
    ) -> list[AgentSessionLogEntry] | None:
        if (
            "session_session_log" not in resource.relations_to
            or len(resource.relations_to["session_session_log"]) == 0
        ):
            raise ValueError("Session log must have session relation")

        if len(resource.relations_to["session_session_log"]) != 1:
            raise ValueError("Session log must have exactly one session relation")

        if (
            expanded_resources_to.get("session_session_log")
            and expanded_resources_to["session_session_log"][0].metadata.get("unattached") == "true"
        ):
            return None

        if resource.found is not True:
            return None

        assert isinstance(resource.payload, list)

        session_ref = resource.relations_to["session_session_log"][0]
        if not isinstance(session_ref, SessionRef):
            raise ValueError("Session log session relation is not a session")
        session = format_session_reference(session_ref)

        entries: list[AgentSessionLogEntry] = []

        for index, record_raw in enumerate(resource.payload):
            try:
                record_data = json.loads(record_raw)
            except json.JSONDecodeError:
                record_data = None

            entries.append(
                AgentSessionLogEntry(
                    session=session,
                    entry_index=index,
                    parsed=record_data is not None,
                    raw=record_raw if record_data is None else None,
                    data=format_agent_session_log_entry(record_data) if record_data is not None else None,
                )
            )

        return entries


def _empty_str_to_none(value: str | None) -> str | None:
    return None if value == "" else value


def parse_created(value: int | str | None) -> dt.datetime | None:
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            value = int(text)
        else:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = dt.datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)

    if value > 10**12:
        value = int(value / 1000)
    return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)

def format_content_filter_category(raw: Mapping[str, Any]) -> ContentFilterCategory:
    return ContentFilterCategory(
        filtered=raw["filtered"],
        severity=raw["severity"],
    )

def format_content_filter_results(raw: Mapping[str, Any]) -> ContentFilterResults:
    return ContentFilterResults(
        hate=format_content_filter_category(raw["hate"]) if "hate" in raw else None,
        self_harm=format_content_filter_category(raw["self_harm"]) if "self_harm" in raw else None,
        sexual=format_content_filter_category(raw["sexual"]) if "sexual" in raw else None,
        violence=format_content_filter_category(raw["violence"]) if "violence" in raw else None,
    )

def format_prompt_filter_result(raw: Mapping[str, Any]) -> PromptFilterResult:
    return PromptFilterResult(
        prompt_index=raw["prompt_index"],
        content_filter_results=format_content_filter_results(raw["content_filter_results"]),
    )

def format_citation(raw: Mapping[str, Any]) -> Citation:
    return Citation(
        ip_type=raw.get("ip_type"),
        license=raw.get("license"),
        snippet=raw.get("snippet"),
        url=raw.get("url"),
    )

def format_citation_entry(raw: Mapping[str, Any]) -> CitationEntry:
    citations = raw.get("citations")
    return CitationEntry(
        citations=format_citation(citations) if isinstance(citations, dict) else None,
        end_offset=raw.get("end_offset"),
        id=raw.get("id"),
        start_offset=raw.get("start_offset"),
    )

def format_copilot_annotations(raw: str | Mapping[str, Any] | None) -> CopilotAnnotations | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return CopilotAnnotations(IPCodeCitations=None, citations=None, raw=raw)
    ip_citations = raw.get("IPCodeCitations")
    citations = raw.get("citations")
    return CopilotAnnotations(
        IPCodeCitations=[format_citation_entry(x) for x in ip_citations] if ip_citations is not None else None,
        citations=[format_citation_entry(x) for x in citations] if citations is not None else None,
        raw=None,
    )

def format_delta_tool_call(raw: Mapping[str, Any]) -> DeltaToolCall:
    fn = raw.get("function") or {}
    custom = raw.get("custom") or {}
    return DeltaToolCall(
        function_name=fn.get("name"),
        function_arguments=fn.get("arguments"),
        custom_name=custom.get("name"),
        custom_input=custom.get("input"),
        id=raw.get("id"),
        index=raw.get("index"),
        type=raw.get("type"),
    )

def format_message_tool_call(raw: Mapping[str, Any]) -> MessageToolCall:
    fn = raw.get("function") or {}
    return MessageToolCall(
        function_name=fn.get("name"),
        function_arguments=fn.get("arguments"),
        id=raw.get("id"),
        type=raw.get("type"),
    )

def format_delta(raw: Mapping[str, Any]) -> Delta:
    return Delta(
        content=raw.get("content"),
        copilot_annotations=format_copilot_annotations(raw.get("copilot_annotations")),
        encrypted_content=raw.get("encrypted_content"),
        padding=raw.get("padding"),
        phase=raw.get("phase"),
        reasoning_opaque=raw.get("reasoning_opaque"),
        reasoning_text=raw.get("reasoning_text"),
        role=raw.get("role"),
        tool_calls=[format_delta_tool_call(x) for x in raw["tool_calls"]] if raw.get("tool_calls") is not None else None,
    )

def format_message(raw: Mapping[str, Any]) -> Message:
    return Message(
        content=raw.get("content"),
        role=raw.get("role"),
        tool_calls=[format_message_tool_call(x) for x in raw["tool_calls"]] if raw.get("tool_calls") is not None else None,
    )

def format_choice(raw: Mapping[str, Any]) -> Choice:
    return Choice(
        content_filter_results=format_content_filter_results(raw["content_filter_results"]) if raw.get("content_filter_results") is not None else None,
        delta=format_delta(raw["delta"]),
        finish_reason=raw.get("finish_reason"),
        index=raw.get("index"),
        message=format_message(raw["message"]) if raw.get("message") is not None else None,
    )

def format_content_part(raw: Mapping[str, Any]) -> ContentPart:
    image_url_obj = raw.get("image_url")
    if isinstance(image_url_obj, str):
        image_url = image_url_obj
    elif isinstance(image_url_obj, dict):
        image_url = image_url_obj.get("url")
    else:
        image_url = None

    return ContentPart(
        type=raw["type"],
        text=raw.get("text"),
        image_url=image_url,
    )

def format_content(raw: str | list[Mapping[str, Any]] | None) -> list[ContentPart] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return [ContentPart(type="text", text=raw, image_url=None)]
    return [format_content_part(x) for x in raw]

def format_copilot_billing_metadata(raw: Mapping[str, Any]) -> CopilotBillingMetadata:
    return CopilotBillingMetadata(billable=raw["billable"])

def format_copilot_info_message(raw: Mapping[str, Any]) -> CopilotInfoMessage:
    return CopilotInfoMessage(code=raw["code"], message=raw["message"])

def format_copilot_warning_message(raw: Mapping[str, Any]) -> CopilotWarningMessage:
    return CopilotWarningMessage(code=raw["code"], message=raw["message"])

def format_token_detail(raw: Mapping[str, Any]) -> TokenDetail:
    return TokenDetail(
        batch_size=raw["batch_size"],
        cost_per_batch=raw["cost_per_batch"],
        token_count=raw["token_count"],
        token_type=raw["token_type"],
    )

def format_copilot_usage(raw: Mapping[str, Any]) -> CopilotUsage:
    token_details = raw.get("token_details")
    return CopilotUsage(
        token_details=[format_token_detail(x) for x in token_details] if token_details is not None else [],
        total_nano_aiu=raw["total_nano_aiu"],
    )

def format_error_info(raw: Mapping[str, Any]) -> ErrorInfo:
    return ErrorInfo(code=raw["code"], message=raw["message"])

def format_completion_tokens_details(raw: Mapping[str, Any]) -> CompletionTokensDetails:
    return CompletionTokensDetails(
        accepted_prediction_tokens=raw.get("accepted_prediction_tokens"),
        reasoning_tokens=raw.get("reasoning_tokens"),
        rejected_prediction_tokens=raw.get("rejected_prediction_tokens"),
    )

def format_prompt_tokens_details(raw: Mapping[str, Any]) -> PromptTokensDetails:
    return PromptTokensDetails(
        cache_creation_tokens=raw.get("cache_creation_tokens"),
        cached_tokens=raw["cached_tokens"],
        input_tokens=raw.get("input_tokens"),
        output_tokens=raw.get("output_tokens"),
    )

def format_usage_copilot_usage(raw: Mapping[str, Any]) -> UsageCopilotUsage:
    return UsageCopilotUsage(
        token_details=[format_token_detail(x) for x in raw["token_details"]],
        total_nano_aiu=raw["total_nano_aiu"],
    )

def format_usage(raw: Mapping[str, Any]) -> Usage:
    return Usage(
        completion_tokens=raw["completion_tokens"],
        completion_tokens_details=format_completion_tokens_details(raw["completion_tokens_details"]) if raw.get("completion_tokens_details") is not None else None,
        copilot_usage=format_usage_copilot_usage(raw["copilot_usage"]) if raw.get("copilot_usage") is not None else None,
        prompt_tokens=raw["prompt_tokens"],
        prompt_tokens_details=format_prompt_tokens_details(raw["prompt_tokens_details"]) if raw.get("prompt_tokens_details") else None,
        reasoning_tokens=raw.get("reasoning_tokens"),
        time_in_ms=raw.get("time_in_ms"),
        total_tokens=raw["total_tokens"],
    )

def format_tool_telemetry_metrics(raw: object) -> ToolTelemetryMetrics | None:
    if not isinstance(raw, dict):
        return None
    return ToolTelemetryMetrics(
        agent_count=raw.get("agent_count"),
        callCount=raw.get("callCount"),
        cancelled_count=raw.get("cancelled_count"),
        cloudRowsReturned=raw.get("cloudRowsReturned"),
        codeql_alertCount=raw.get("codeql.alertCount"),
        codeql_duration_ms=raw.get("codeql.duration.ms"),
        codeql_languages_count=raw.get("codeql.languages.count"),
        codeql_languages_skipped_count=raw.get("codeql.languages.skipped_count"),
        codeql_total_alerts=raw.get("codeql.total.alerts"),
        codeReview_alertCount=raw.get("codeReview.alertCount"),
        codeReview_durationMs=raw.get("codeReview.durationMs"),
        commandTimeout=raw.get("commandTimeout"),
        commentsExcluded=raw.get("commentsExcluded"),
        commentsGenerated=raw.get("commentsGenerated"),
        compacted_saved_chars=raw.get("compacted_saved_chars"),
        completed_count=raw.get("completed_count"),
        completedStatements=raw.get("completedStatements"),
        definitionCount=raw.get("definitionCount"),
        delivered_count=raw.get("delivered_count"),
        duration_seconds=raw.get("duration_seconds"),
        elapsed_seconds=raw.get("elapsed_seconds"),
        exit_code=raw.get("exit_code"),
        failed_count=raw.get("failed_count"),
        file_count=raw.get("file_count"),
        hasContent=raw.get("hasContent"),
        idle_count=raw.get("idle_count"),
        linesAdded=raw.get("linesAdded"),
        linesRemoved=raw.get("linesRemoved"),
        localRowsReturned=raw.get("localRowsReturned"),
        mcp_result_content_bytes=raw.get("mcp_result_content_bytes"),
        mcp_structured_content_bytes=raw.get("mcp_structured_content_bytes"),
        mcp_task_count=raw.get("mcp_task_count"),
        message_length=raw.get("message_length"),
        numberOfToolCallsMadeByAgent=raw.get("numberOfToolCallsMadeByAgent"),
        originalContentLength=raw.get("originalContentLength"),
        queue_depth=raw.get("queue_depth"),
        redirectCount=raw.get("redirectCount"),
        requested_recipient_count=raw.get("requested_recipient_count"),
        resolved_recipient_count=raw.get("resolved_recipient_count"),
        response_length=raw.get("response_length"),
        responseTokenLimit=raw.get("responseTokenLimit"),
        result_length=raw.get("result_length"),
        result_length_original=raw.get("result_length_original"),
        resultForLlmLength=raw.get("resultForLlmLength"),
        resultLength=raw.get("resultLength"),
        returnedContentLength=raw.get("returnedContentLength"),
        reviewedFiles=raw.get("reviewedFiles"),
        rowsAffected=raw.get("rowsAffected"),
        rowsReturned=raw.get("rowsReturned"),
        running_count=raw.get("running_count"),
        skillContentLength=raw.get("skillContentLength"),
        skipped_count=raw.get("skipped_count"),
        startIndex=raw.get("startIndex"),
        statementCount=raw.get("statementCount"),
        symbolCount=raw.get("symbolCount"),
        timeout_seconds=raw.get("timeout_seconds"),
        total_turns=raw.get("total_turns"),
        tracked_shutdown_count=raw.get("tracked_shutdown_count"),
        validation_budgetSeconds=raw.get("validation.budgetSeconds"),
        validation_codeQLDurationMs=raw.get("validation.codeQLDurationMs"),
        validation_codeReviewDurationMs=raw.get("validation.codeReviewDurationMs"),
        validation_iteration=raw.get("validation.iteration"),
        validation_remainingBudgetMs=raw.get("validation.remainingBudgetMs"),
        validation_totalDurationMs=raw.get("validation.totalDurationMs"),
    )

def format_tool_telemetry_properties(raw: object) -> ToolTelemetryProperties | None:
    if not isinstance(raw, dict):
        return None
    return ToolTelemetryProperties(
        agent_id=raw.get("agent_id"),
        agent_name=raw.get("agent_name"),
        agent_name_hash=raw.get("agent_name_hash"),
        agent_type=raw.get("agent_type"),
        asyncOnlyShell=raw.get("asyncOnlyShell"),
        backend=raw.get("backend"),
        character=raw.get("character"),
        codeBlocks=raw.get("codeBlocks"),
        codeReviewFileExtensions=raw.get("codeReviewFileExtensions"),
        codeReviewModel=raw.get("codeReviewModel"),
        codeReviewResult=raw.get("codeReviewResult"),
        codeReviewTimedOut=raw.get("codeReviewTimedOut"),
        codeReview_engine=raw.get("codeReview.engine"),
        codeReview_skipReason=raw.get("codeReview.skipReason"),
        codeql_aborted=raw.get("codeql.aborted"),
        codeql_analysisRuleIds=raw.get("codeql.analysisRuleIds"),
        codeql_languages=raw.get("codeql.languages"),
        codeql_languagesAttempted=raw.get("codeql.languagesAttempted"),
        codeql_skipReason=raw.get("codeql.skipReason"),
        codeql_version=raw.get("codeql.version"),
        command=raw.get("command"),
        commentQueryNames=raw.get("commentQueryNames"),
        current_value=raw.get("current_value"),
        customTimeout=raw.get("customTimeout"),
        database=raw.get("database"),
        delivery_status=raw.get("delivery_status"),
        detached=raw.get("detached"),
        error=raw.get("error"),
        execution_mode=raw.get("execution_mode"),
        executionMode=raw.get("executionMode"),
        failedStatementType=raw.get("failedStatementType"),
        file_hash=raw.get("file_hash"),
        file_type=raw.get("file_type"),
        fileExtension=raw.get("fileExtension"),
        files_found=raw.get("files_found"),
        found=raw.get("found"),
        hashedUrl=raw.get("hashedUrl"),
        inputs=raw.get("inputs"),
        is_timeout=raw.get("is_timeout"),
        language_server=raw.get("language_server"),
        languageId=raw.get("languageId"),
        languages=raw.get("languages"),
        large_output=raw.get("large_output"),
        largeOutputAvoided=raw.get("largeOutputAvoided"),
        largeOutputHandled=raw.get("largeOutputHandled"),
        largeOutputJsonFormatted=raw.get("largeOutputJsonFormatted"),
        largeOutputOriginalSizeBytes=raw.get("largeOutputOriginalSizeBytes"),
        largeOutputWrittenToFile=raw.get("largeOutputWrittenToFile"),
        limit_type=raw.get("limit_type"),
        limit_value=raw.get("limit_value"),
        line=raw.get("line"),
        matches_found=raw.get("matches_found"),
        mimeType=raw.get("mimeType"),
        model=raw.get("model"),
        operation=raw.get("operation"),
        options=raw.get("options"),
        output_mode=raw.get("output_mode"),
        outputTruncated=raw.get("outputTruncated"),
        prompt_length=raw.get("prompt_length"),
        queryType=raw.get("queryType"),
        raw=raw.get("raw"),
        read_target_original_mode=raw.get("read_target_original_mode"),
        read_target_state=raw.get("read_target_state"),
        readError=raw.get("readError"),
        resolved_model=raw.get("resolved_model"),
        resolvedPathAgainstCwd=raw.get("resolvedPathAgainstCwd"),
        response_length=raw.get("response_length"),
        sandboxApplied=raw.get("sandboxApplied"),
        sandboxOptOutRequested=raw.get("sandboxOptOutRequested"),
        scope=raw.get("scope"),
        selection_kind=raw.get("selection_kind"),
        shell_error_category=raw.get("shell_error_category"),
        shell_operation=raw.get("shell_operation"),
        shell_status=raw.get("shell_status"),
        skillNameHash=raw.get("skillNameHash"),
        skillSource=raw.get("skillSource"),
        statementTypes=raw.get("statementTypes"),
        status=raw.get("status"),
        timed_out=raw.get("timed_out"),
        trivialChange_alertCount=raw.get("trivialChange.alertCount"),
        trivialChange_codeQL_durationMs=raw.get("trivialChange.codeQL.durationMs"),
        trivialChange_codeQL_isTrivial=raw.get("trivialChange.codeQL.isTrivial"),
        trivialChange_disagreement=raw.get("trivialChange.disagreement"),
        trivialChange_isTrivial=raw.get("trivialChange.isTrivial"),
        validation_budgetResetEnabled=raw.get("validation.budgetResetEnabled"),
        validation_codeQL_skipReason=raw.get("validation.codeQL.skipReason"),
        validation_codeQLEnabled=raw.get("validation.codeQLEnabled"),
        validation_codeQLSuccess=raw.get("validation.codeQLSuccess"),
        validation_codeQLTimedOut=raw.get("validation.codeQLTimedOut"),
        validation_codeReview_skipReason=raw.get("validation.codeReview.skipReason"),
        validation_codeReviewEnabled=raw.get("validation.codeReviewEnabled"),
        validation_codeReviewSuccess=raw.get("validation.codeReviewSuccess"),
        validation_codeReviewTimedOut=raw.get("validation.codeReviewTimedOut"),
        validation_consecutiveTimeouts=raw.get("validation.consecutiveTimeouts"),
        validation_invalidInput=raw.get("validation.invalidInput"),
        validation_jobStarted=raw.get("validation.jobStarted"),
        validation_languages=raw.get("validation.languages"),
        validation_retryGuidance=raw.get("validation.retryGuidance"),
        validation_skipReason=raw.get("validation.skipReason"),
        validation_skipped=raw.get("validation.skipped"),
        viewType=raw.get("viewType"),
        wasSyntaxError=raw.get("wasSyntaxError"),
    )

def format_tool_telemetry_restricted(raw: object) -> ToolTelemetryRestrictedProperties | None:
    if not isinstance(raw, dict):
        return None
    return ToolTelemetryRestrictedProperties(
        addedPaths=raw.get("addedPaths"),
        agent_id=raw.get("agent_id"),
        agent_name=raw.get("agent_name"),
        cloudError=raw.get("cloudError"),
        codeql_error=raw.get("codeql.error"),
        codeql_stack=raw.get("codeql.stack"),
        codeReviewError=raw.get("codeReviewError"),
        deletedPaths=raw.get("deletedPaths"),
        domParsingError=raw.get("domParsingError"),
        error=raw.get("error"),
        error_detail=raw.get("error_detail"),
        errorMessage=raw.get("errorMessage"),
        file=raw.get("file"),
        filePaths=raw.get("filePaths"),
        filesReviewed=raw.get("filesReviewed"),
        finalUrl=raw.get("finalUrl"),
        large_output_file=raw.get("large_output_file"),
        largeOutputFilePath=raw.get("largeOutputFilePath"),
        path=raw.get("path"),
        pattern=raw.get("pattern"),
        pluginName=raw.get("pluginName"),
        prTitle=raw.get("prTitle"),
        query=raw.get("query"),
        shell_id=raw.get("shell_id"),
        skillName=raw.get("skillName"),
        trivialChange_codeQL_reason=raw.get("trivialChange.codeQL.reason"),
        trivialChange_reason=raw.get("trivialChange.reason"),
        url=raw.get("url"),
        validation_error=raw.get("validation.error"),
    )

def format_tool_telemetry(raw: Mapping[str, Any]) -> ToolTelemetry:
    return ToolTelemetry(
        event=raw.get("event"),
        metrics=format_tool_telemetry_metrics(raw.get("metrics")),
        properties=format_tool_telemetry_properties(raw.get("properties")),
        restrictedProperties=format_tool_telemetry_restricted(raw.get("restrictedProperties")),
    )

def format_truncate_result(raw: Mapping[str, Any]) -> TruncateResult:
    return TruncateResult(
        messagesRemovedDuringTruncation=raw["messagesRemovedDuringTruncation"],
        postTruncationMessagesLength=raw["postTruncationMessagesLength"],
        postTruncationTokensInMessages=raw["postTruncationTokensInMessages"],
        preTruncationMessagesLength=raw["preTruncationMessagesLength"],
        preTruncationTokensInMessages=raw["preTruncationTokensInMessages"],
        tokenLimit=raw["tokenLimit"],
        tokensRemovedDuringTruncation=raw["tokensRemovedDuringTruncation"],
    )

def format_agent_session_log_entry(raw: Mapping[str, Any]) -> AgentSessionLogEntryData:
    model_call = raw.get("modelCall")

    return AgentSessionLogEntryData(
        id=raw.get("id"),
        agentId=raw.get("agentId"),
        callId=raw.get("callId"),
        choices=[format_choice(x) for x in raw["choices"]] if raw.get("choices") is not None else None,
        content=format_content(raw.get("content")),
        copilotBillingMetadata=format_copilot_billing_metadata(raw["copilotBillingMetadata"]) if raw.get("copilotBillingMetadata") is not None else None,
        copilot_info_messages=[format_copilot_info_message(x) for x in raw["copilot_info_messages"]] if raw.get("copilot_info_messages") is not None else None,
        copilot_model_warning_message=raw.get("copilot_model_warning_message"),
        copilot_usage=format_copilot_usage(raw["copilot_usage"]) if raw.get("copilot_usage") else None,
        copilot_warning_messages=[format_copilot_warning_message(x) for x in raw["copilot_warning_messages"]] if raw.get("copilot_warning_messages") is not None else None,
        created=parse_created(raw.get("created")),
        error=format_error_info(raw["error"]) if raw.get("error") is not None else None,
        kind=raw.get("kind"),
        model=_empty_str_to_none(raw.get("model")),
        modelCall_error=model_call.get("error") if isinstance(model_call, dict) else None,
        modelCallDurationMs=raw.get("modelCallDurationMs"),
        object=raw.get("object"),
        performedBy=raw.get("performedBy"),
        prompt_filter_results=[format_prompt_filter_result(x) for x in raw["prompt_filter_results"]] if raw.get("prompt_filter_results") is not None else None,
        role=raw.get("role"),
        source=raw.get("source"),
        system_fingerprint=raw.get("system_fingerprint"),
        tool_call_id=raw.get("tool_call_id"),
        toolTelemetry=format_tool_telemetry(raw["toolTelemetry"]) if raw.get("toolTelemetry") is not None else None,
        truncateResult=format_truncate_result(raw["truncateResult"]) if raw.get("truncateResult") is not None else None,
        turn=raw.get("turn"),
        usage=format_usage(raw["usage"]) if raw.get("usage") else None,
    )