"""JARVIS Command Router.

Parses and dispatches administrative, security, and tool commands from the CLI interface.
Maintains deterministic routing and safety boundaries.
"""

from __future__ import annotations

import json
import logging
import re
import shlex
from typing import Any, Dict, List, Optional
from config import OperatingMode, PermissionType
from core.assistant import JarvisAssistant

logger = logging.getLogger("jarvis.core.router")


class CommandRouter:
    """Dispatches text commands to the appropriate assistant subsystem."""

    def __init__(self, assistant: JarvisAssistant):
        self.assistant = assistant
        self.assistant.set_router(self)

    async def handle_command(self, raw_input: str) -> str:
        """Parse and execute a text command."""
        text = raw_input.strip()
        if not text:
            return ""

        # User interaction resets the 60-second inactivity sleep timer
        if hasattr(self.assistant, "voice"):
            self.assistant.voice.reset_activity()

        lower_text = text.lower()

        # 1. System status
        if lower_text in ("status", "jzt jarvis status", "health"):
            report = self.assistant.get_status_report()
            lines = [
                "=== JARVIS System Status ===",
                f"Assistant Name:       {report['assistant_name']} v{report['version']}",
                f"Operating Mode:       {report['operating_mode']}",
                f"Safe Mode:            {report['safe_mode']}",
                f"Emergency Stop:       {'ACTIVE' if report['emergency_stopped'] else 'INACTIVE'}",
                f"Microphone:           {report['microphone_permission']}",
                f"Internet:             {report['internet_permission']}",
                f"Memory:               {report.get('memory_permission', 'BLOCKED')}",
                f"Memory Subsystem:     {report.get('memory_subsystem', 'OFF')}",
                f"Voice Subsystem:      {report['voice_subsystem']}",
                f"AI Provider:          {report['ai_provider']}",
                f"Database:             {report['database_status']}",
                f"Registered Tools:     {report['registered_tools_count']}",
                f"Automation:           {report['automation_subsystem']}",
                "============================",
            ]
            return "\n".join(lines)

        # 2. Permission Commands
        if lower_text in ("permission status", "permissions"):
            statuses = self.assistant.permissions.get_all_statuses()
            lines = ["=== JARVIS Permission Status ==="]
            for perm, status in sorted(statuses.items()):
                mark = "[ALLOWED]" if status == "allowed" else "[BLOCKED]"
                lines.append(f"{perm:<15} : {mark}")
            lines.append("================================")
            return "\n".join(lines)

        if lower_text.startswith("allow "):
            perm_name = lower_text.split("allow ", 1)[1].strip()
            try:
                self.assistant.permissions.allow(perm_name, "Granted via CLI command")
                return f"Permission '{perm_name}' has been ALLOWED."
            except ValueError as e:
                return f"Error: {e}"

        if lower_text.startswith("block "):
            perm_name = lower_text.split("block ", 1)[1].strip()
            if perm_name == "all":
                self.assistant.permissions.block_all("Revoked via CLI 'block all'")
                return "ALL permissions have been BLOCKED."
            try:
                self.assistant.permissions.block(perm_name, "Revoked via CLI command")
                return f"Permission '{perm_name}' has been BLOCKED."
            except ValueError as e:
                return f"Error: {e}"

        # 3. Emergency Stop Commands
        if lower_text in ("emergency stop", "jzt jarvis emergency stop"):
            self.assistant.security.trigger_emergency_stop("Triggered by user command")
            return "EMERGENCY STOP ENGAGED. All tool executions are halted and locked."

        if lower_text in ("reset emergency stop", "reset emergency"):
            self.assistant.security.reset_emergency_stop()
            return "Emergency stop has been RESET. Normal operations restored."

        # Voice Interruption & Stop Commands
        if self.assistant.voice.is_interrupt_phrase(text):
            was_speaking = self.assistant.voice.interrupt()
            if was_speaking:
                return "Playback interrupted."
            return "Cancelled."

        # 4. Safe Mode Commands
        if lower_text.startswith("safe mode "):
            arg = lower_text.split("safe mode ", 1)[1].strip()
            if arg in ("on", "enable", "1", "true"):
                self.assistant.security.set_safe_mode(True)
                return "Safe Mode ENABLED (HIGH and CRITICAL operations prohibited)."
            elif arg in ("off", "disable", "0", "false"):
                self.assistant.security.set_safe_mode(False)
                return "Safe Mode DISABLED (HIGH and CRITICAL operations permitted with confirmation)."
            else:
                return "Usage: safe mode on | safe mode off"

        # 5. Operating Mode Commands
        if lower_text.startswith("mode "):
            mode_name = lower_text.split("mode ", 1)[1].strip()
            try:
                new_mode = OperatingMode(mode_name)
                self.assistant.security.set_operating_mode(new_mode)
                return f"Operating mode switched to {new_mode.value.upper()}."
            except ValueError:
                return f"Invalid mode '{mode_name}'. Valid modes: offline, hybrid, online."

        # 6. Tools Catalog
        if lower_text in ("tools", "list tools"):
            tools_meta = self.assistant.registry.get_metadata_list()
            lines = ["=== Registered Approved Tools ==="]
            for t in tools_meta:
                lines.append(
                    f"- {t['name']:<16} | Risk: {t['risk_level']:<8} | Perm: {t['permission']:<12} | Confirm: {t['confirmation']:<6}"
                )
                lines.append(f"  Description: {t['description']}")
            lines.append("=================================")
            return "\n".join(lines)

        # 7. Run Tool Command: run <tool_name> [json_args]
        if lower_text.startswith("run "):
            parts = text.split(maxsplit=2)
            if len(parts) < 2:
                return "Usage: run <tool_name> [json_args]"
            tool_name = parts[1]
            args_dict: Dict[str, Any] = {}
            if len(parts) >= 3:
                raw_json = parts[2].strip()
                try:
                    args_dict = json.loads(raw_json)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON arguments: {e}"

            result = await self.assistant.execute_tool(tool_name, args_dict)
            if result.success:
                return f"Tool Execution Succeeded:\nMessage: {result.message}\nData: {json.dumps(result.data, indent=2)}"
            else:
                return f"Tool Execution Failed:\nMessage: {result.message}\nError: {result.error}"

        # 8. Phase 2 Safe PC Shortcuts: 'open <app|folder>'
        if lower_text.startswith("open "):
            clean_open = re.sub(r'[\.\?\!\,\;]+$', '', text).strip()
            target = clean_open[5:].strip()
            if not target:
                return "Usage: open <app_name | folder_name> (e.g. 'open Chrome', 'open Downloads')"
            target_lower = target.lower()

            # Folder launcher (handle standard folder names and variations like 'my downloads', 'downloads folder')
            if target_lower in ("desktop", "documents", "downloads") or any(target_lower == f"my {f}" or target_lower == f"the {f}" or target_lower == f"{f} folder" for f in ("desktop", "documents", "downloads")):
                folder_key = "downloads" if "download" in target_lower else ("documents" if "document" in target_lower else "desktop")
                result = await self.assistant.execute_tool("open_folder", {"folder_name": folder_key})
            else:
                # Application launcher
                result = await self.assistant.execute_tool("open_application", {"app_name": target})

            if result.success:
                return f"Success: {result.message}"
            else:
                return f"Failed: {result.message}\nError: {result.error}"

        # 9. Phase 2 File Search Shortcut: 'find <query>' or 'search <query>'
        if lower_text.startswith("find ") or lower_text.startswith("search "):
            query = text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) > 1 else ""
            if not query:
                return "Usage: find <query> (e.g. 'find Python files', 'find *.pdf')"

            result = await self.assistant.execute_tool("search_files", {"query": query})
            if result.success:
                res_data = result.data or {}
                matches = res_data.get("results", [])
                if not matches:
                    return f"No files found matching query '{query}' in user folders."
                lines = [f"=== Found {len(matches)} Matching File(s) for '{query}' ==="]
                for m in matches:
                    lines.append(f"- {m['filename']} ({m.get('size_kb', 0)} KB) -> {m.get('path', '')}")
                lines.append("==================================================")
                return "\n".join(lines)
            else:
                return f"Search failed: {result.message}\nError: {result.error}"

        # 8. Audit Logs
        if lower_text.startswith("audit"):
            parts = lower_text.split()
            limit = 10
            if len(parts) > 1 and parts[1].isdigit():
                limit = int(parts[1])
            entries = self.assistant.audit.get_recent_entries(limit=limit)
            if not entries:
                return "No audit entries recorded yet."
            lines = [f"=== Recent Audit Entries (Last {len(entries)}) ==="]
            for e in entries:
                lines.append(
                    f"[{e.timestamp[:19]}] Action: {e.action} | Result: {e.result} | Risk: {e.risk_level} | Tool: {e.tool_name or 'N/A'}"
                )
                if e.error_details:
                    lines.append(f"   Error: {e.error_details}")
            lines.append("===========================================")
            return "\n".join(lines)

        # 9. Voice Interaction Commands (Phase 3)
        if lower_text in ("voice status", "voice"):
            v = self.assistant.voice
            mic_ok = self.assistant.permissions.is_allowed(PermissionType.MICROPHONE)
            lines = [
                "=== JARVIS Voice Subsystem Status ===",
                f"Voice State:          {v.state.value}",
                f"Listening Loop:       {'ACTIVE' if v.is_active else 'INACTIVE'}",
                f"Microphone:           {'ALLOWED' if mic_ok else 'BLOCKED'}",
                f"Configured Wake Word: '{self.assistant.settings.wake_phrase}'",
                f"STT Provider:         {v.stt.get_provider_name()}",
                f"TTS Provider:         {v.tts.get_provider_name()}",
                f"TTS Enabled:          {self.assistant.settings.tts_enabled}",
                "=====================================",
            ]
            return "\n".join(lines)

        if lower_text in ("start listening", "voice start"):
            if not self.assistant.permissions.is_allowed(PermissionType.MICROPHONE):
                return "Could not start voice listener. Microphone permission is BLOCKED. Run 'allow microphone' first."
            if not self.assistant.voice.stt.is_available():
                return "Could not start voice listener. Audio capture hardware/driver is unavailable."
            success = self.assistant.voice.start_listening()
            if success:
                return f"Voice listener started. Speak the wake phrase ('{self.assistant.settings.wake_phrase}') to begin."
            else:
                return "Could not start voice listener. Check microphone connection and permissions."

        if lower_text in ("stop listening", "voice stop"):
            self.assistant.voice.stop_listening()
            return "Voice listener stopped. JARVIS is in SLEEP mode."

        if lower_text in ("voice mute", "mute"):
            self.assistant.voice.mute()
            return "Microphone has been MUTED. Voice capture and wake-word detection are stopped."

        if lower_text in ("voice unmute", "unmute"):
            ok = self.assistant.voice.unmute()
            if ok:
                return "Microphone has been UNMUTED. Local wake-word detection is active."
            return "Microphone unmuted, but microphone permission is BLOCKED. Run 'allow microphone' first."

        if lower_text in ("voice wake", "wake", "wake up"):
            self.assistant.voice.wake_up()
            return "JARVIS is AWAKE. 60-second inactivity timer active."

        if lower_text in ("voice sleep", "sleep", "go to sleep"):
            self.assistant.voice.sleep()
            return "JARVIS has entered SLEEP mode. Listening locally for wake word 'Jarvis'."

        if lower_text.startswith("voice simulate "):
            speech = text[15:].strip()
            if not speech:
                return "Usage: voice simulate <spoken_transcript>"
            spoken_res = await self.assistant.voice.process_voice_input(speech)
            return f"Voice Simulation Result:\nSpoken response: \"{spoken_res}\"\nCurrent Voice State: {self.assistant.voice.state.value}"

        if lower_text.startswith("voice say "):
            say_text = text[10:].strip()
            if not say_text:
                return "Usage: voice say <text>"
            await self.assistant.voice.tts.speak(say_text)
            return f"Speaking: \"{say_text}\""

        if lower_text.startswith("wake phrase "):
            phrase = text[12:].strip()
            if not phrase:
                return "Usage: wake phrase <new_phrase>"
            self.assistant.settings.wake_phrase = phrase
            self.assistant.voice.wake_detector.set_wake_phrase(phrase)
            return f"Wake phrase updated to: '{phrase}'"

        # 10. AI Brain Commands (Phase 4)
        if lower_text in ("ai status", "ai"):
            b = self.assistant.brain
            p = b.provider
            info = p.get_model_info()
            resources = b.get_resource_usage()
            cloud_ai_status = "ALLOWED" if self.assistant.permissions.is_allowed(PermissionType.CLOUD_AI) else "BLOCKED"
            lines = [
                "=== JARVIS AI Brain Status ===",
                f"AI Enabled:           {self.assistant.settings.ai_enabled}",
                f"AI Mode:              {self.assistant.settings.ai_mode.upper()}",
                f"AI Provider:          {p.name}",
                f"Provider Available:   {p.is_available()}",
                f"Configured Model:     {info.get('configured_model', 'N/A')}",
                f"Status:               {info.get('status', 'Ready')}",
                f"Cloud AI Permission:  {cloud_ai_status}",
                f"Process Memory (RSS): {resources['process_rss_mb']} MB",
                f"System RAM Used:      {resources['system_ram_percent_used']}% ({resources['system_available_ram_gb']} GB free)",
                f"RAM Safety Policy:    8 GB Laptop Optimized (Auto-download BLOCKED)",
                "===============================",
            ]
            return "\n".join(lines)

        if lower_text.startswith("ask "):
            prompt = text[4:].strip()
            if not prompt:
                return "Usage: ask <natural language prompt>"
            brain_res = await self.assistant.brain.think(prompt)
            lines = [
                f"=== AI Brain Result ({brain_res.provider_used} / {brain_res.model_used}) ===",
                f"Response:       \"{brain_res.spoken_response}\"",
            ]
            if brain_res.tool_planned:
                lines.append(f"Tool Planned:   {brain_res.tool_planned}")
                lines.append(f"Tool Arguments: {json.dumps(brain_res.tool_arguments)}")
                if brain_res.tool_result:
                    status_str = "SUCCESS" if brain_res.tool_result.success else "FAILED"
                    lines.append(f"Execution:      {status_str} ({brain_res.tool_result.message})")
            if brain_res.diagnostic_trace:
                lines.append("\n" + brain_res.diagnostic_trace.format_log())
            if brain_res.is_clarification:
                lines.append("Type:           Clarification Question")
            if brain_res.error:
                lines.append(f"Error:          {brain_res.error}")
            lines.append("==================================================")
            return "\n".join(lines)

        if lower_text in ("ai models", "ai list models", "ai recommendations"):
            from ai.local_provider import LIGHTWEIGHT_MODEL_RECOMMENDATIONS
            lines = [
                "=== Lightweight Local AI Models for 8 GB RAM ===",
                "NOTE: JARVIS never automatically downloads models.",
                "To install, use Ollama locally with explicit approval.",
                "-------------------------------------------------",
            ]
            for r in LIGHTWEIGHT_MODEL_RECOMMENDATIONS:
                rec_badge = " [RECOMMENDED]" if r["recommended"] else ""
                lines.append(f"* {r['name']}{rec_badge}")
                lines.append(f"  - Parameters: {r['parameters']} | Size: {r['download_size']} | RAM: {r['expected_ram']}")
                lines.append(f"  - Details: {r['strengths']}")
            lines.append("=================================================")
            return "\n".join(lines)

        if lower_text.startswith("ai mode "):
            mode = lower_text.split("ai mode ", 1)[1].strip()
            if mode in ("local", "online", "hybrid"):
                self.assistant.settings.ai_mode = mode
                if mode == "online":
                    from ai.openrouter_provider import OpenRouterProvider
                    self.assistant.brain.set_provider(
                        OpenRouterProvider(self.assistant.settings, self.assistant.registry, self.assistant.permissions)
                    )
                elif mode == "local":
                    from ai.local_provider import LocalAIProvider
                    self.assistant.brain.set_provider(
                        LocalAIProvider(self.assistant.settings, self.assistant.registry)
                    )
                return f"AI Mode switched to: {mode.upper()}."
            return "Usage: ai mode <local|online|hybrid>"

        # 11. Long-Term Memory & Context Commands (Phase 5)
        if lower_text in ("memory status", "memory health"):
            mem_status = self.assistant.memory.get_status()
            sess_id = self.assistant.context.get_current_session_id()
            diag = self.assistant.context.get_diagnostic_status()
            lines = [
                "=== JARVIS Long-Term Memory Status ===",
                f"Memory Subsystem:     {'ACTIVE' if mem_status['permission'] == 'ALLOWED' else 'OFF (Permission Blocked)'}",
                f"Memory Permission:    {mem_status['permission']}",
                f"Stored Memories:      {mem_status['active_memories']} item(s)",
                f"Active Session ID:    {sess_id}",
                f"Recent Context Turns: {diag['session_history_turns']}",
                f"Memory Feature Flag:  {'ENABLED' if self.assistant.settings.memory_enabled else 'DISABLED'}",
                f"Database Path:        {mem_status['database_path']}",
                "=====================================",
            ]
            return "\n".join(lines)

        if lower_text.startswith("remember "):
            info = text[9:].strip()
            if not info:
                return "Usage: remember <information to store>"
            if not self.assistant.permissions.is_allowed(PermissionType.MEMORY):
                return "Could not save memory. Memory permission is BLOCKED. Run 'allow memory' first."
            success, msg, item = self.assistant.memory.remember(info, source="user_cli")
            if success and item:
                return f"Remembered: \"{item.content}\" (ID: {item.id}, Type: {item.memory_type})"
            return f"Failed to remember: {msg}"

        if lower_text.startswith("forget "):
            target = text[7:].strip()
            if not target:
                return "Usage: forget <search phrase | memory_id>"
            if not self.assistant.permissions.is_allowed(PermissionType.MEMORY):
                return "Could not forget memory. Memory permission is BLOCKED. Run 'allow memory' first."
            success, msg, count = self.assistant.memory.forget(target)
            if success:
                return f"Success: {msg}"
            return f"Failed to forget: {msg}"

        if lower_text in ("memory list", "memories", "list memories"):
            if not self.assistant.permissions.is_allowed(PermissionType.MEMORY):
                return "Memory permission is BLOCKED. Run 'allow memory' to view stored memories."
            memories = self.assistant.memory.list_memories(limit=50)
            if not memories:
                return "No stored memories found."
            lines = [f"=== Stored Long-Term Memories ({len(memories)} item(s)) ==="]
            for m in memories:
                lines.append(f"- [{m.id}] [{m.memory_type.upper()}] (Importance: {m.importance}) \"{m.content}\"")
            lines.append("===============================================")
            return "\n".join(lines)

        if lower_text.startswith("memory search "):
            query = text[14:].strip()
            if not query:
                return "Usage: memory search <search term>"
            if not self.assistant.permissions.is_allowed(PermissionType.MEMORY):
                return "Memory permission is BLOCKED. Run 'allow memory' to search memories."
            matches = self.assistant.memory.search_memories(query=query, limit=10)
            if not matches:
                return f"No memories found matching '{query}'."
            lines = [f"=== Memory Search Results for '{query}' ({len(matches)} item(s)) ==="]
            for m in matches:
                lines.append(f"- [{m.id}] [{m.memory_type.upper()}] \"{m.content}\"")
            lines.append("======================================================")
            return "\n".join(lines)

        if lower_text.startswith("memory view "):
            mid = text[12:].strip()
            if not mid:
                return "Usage: memory view <memory_id>"
            if not self.assistant.permissions.is_allowed(PermissionType.MEMORY):
                return "Memory permission is BLOCKED. Run 'allow memory' to view memories."
            item = self.assistant.memory.get_memory(mid)
            if not item:
                return f"Memory with ID '{mid}' not found."
            lines = [
                f"=== Memory Details [{item.id}] ===",
                f"Content:     \"{item.content}\"",
                f"Type:        {item.memory_type}",
                f"Importance:  {item.importance}",
                f"Source:      {item.source}",
                f"Active:      {item.active}",
                f"Created At:  {item.created_at}",
                f"Updated At:  {item.updated_at}",
                "==================================",
            ]
            return "\n".join(lines)

        if lower_text.startswith("memory delete "):
            mid = text[14:].strip()
            if not mid:
                return "Usage: memory delete <memory_id>"
            if not self.assistant.permissions.is_allowed(PermissionType.MEMORY):
                return "Memory permission is BLOCKED. Run 'allow memory' first."
            deleted = self.assistant.memory.delete_memory(mid)
            if deleted:
                return f"Memory '{mid}' has been permanently deleted."
            return f"Memory with ID '{mid}' not found."

        if lower_text in ("memory clear", "memory clear confirm"):
            if not self.assistant.permissions.is_allowed(PermissionType.MEMORY):
                return "Memory permission is BLOCKED. Run 'allow memory' first."
            if lower_text == "memory clear":
                return "WARNING: This will permanently delete ALL stored memories.\nTo confirm, run: 'memory clear confirm'"
            cleared_count = self.assistant.memory.clear_memories()
            return f"All stored memories cleared successfully ({cleared_count} memory item(s) deleted)."

        # 12. Help
        if lower_text in ("help", "?"):
            return (
                "=== JARVIS Available Commands ===\n"
                "  status                  : Display system and subsystem health status\n"
                "  permissions             : Display permission status list\n"
                "  allow <permission>      : Grant a specific permission (e.g. 'allow memory', 'allow files')\n"
                "  block <permission>      : Revoke a specific permission\n"
                "  block all               : Revoke all permissions immediately\n"
                "  remember <text>         : Remember a fact, preference, or instruction\n"
                "  forget <phrase|id>      : Forget memories matching a phrase or specific ID\n"
                "  memory list             : List all stored long-term memories\n"
                "  memory search <query>   : Search long-term memories\n"
                "  memory view <id>        : View details of a specific memory record\n"
                "  memory delete <id>      : Permanently delete a memory record\n"
                "  memory clear [confirm]  : Clear all stored memories (requires confirmation)\n"
                "  memory status           : Display long-term memory subsystem health\n"
                "  ask <natural language>  : Ask AI Brain to reason, plan safe tools, or answer\n"
                "  ai status               : Display AI Brain, provider, and memory status\n"
                "  ai mode <local|online>  : Switch between local and cloud AI providers\n"
                "  ai models               : List recommended lightweight models for 8 GB RAM\n"
                "  open <app|folder>       : Safely launch app (Chrome, Notepad) or folder (Downloads)\n"
                "  find <pattern>          : Safely search user folders (e.g. 'find Python files')\n"
                "  voice status            : Show voice engine, wake word, and state\n"
                "  start listening         : Engage voice listening loop (requires microphone permission)\n"
                "  stop listening          : Disengage voice listening loop\n"
                "  voice simulate <speech> : Test speech input (e.g. 'voice simulate Jzt Jarvis open Downloads')\n"
                "  voice say <text>        : Speak text using local TTS\n"
                "  wake phrase <phrase>    : Change the active wake phrase\n"
                "  mode <offline|hybrid|online> : Switch operating mode\n"
                "  safe mode <on|off>      : Toggle safe mode\n"
                "  emergency stop          : Trigger immediate emergency stop\n"
                "  reset emergency stop    : Reset emergency stop\n"
                "  tools                   : List approved registered tools\n"
                "  run <tool_name> [json]  : Safely execute a registered tool\n"
                "  audit [limit]           : View recent security audit entries\n"
                "  exit / quit             : Terminate JARVIS session\n"
                "================================="
            )

        # 13. AI Brain Natural Language Fallback (Phase 4 & Phase 5)
        brain_res = await self.assistant.brain.think(text)
        return brain_res.spoken_response
