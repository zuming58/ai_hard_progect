export async function processVoiceRecording({ blob, stt, organizer, organizerOptions, saveHistory, output, outputMode = "history", signal, onPhase }) {
  onPhase?.("transcribing");
  let transcript;
  try { transcript = await stt.transcribe(blob, { signal }); } catch (error) { transcript = { status: "error", text: "", provider: "unknown", durationMs: 0, message: error.message }; }
  let organized = null;
  if (transcript.status === "success") { try { organized = await organizer.organize(transcript.text, organizerOptions); } catch { organized = { text: transcript.text, mode: "raw", fallback: true, message: "整理失败，已保留原始转写" }; } }
  const text = organized?.text || "录音完成，等待转写服务";
  const history = await saveHistory({ text, transcript, organized });
  let outputResult = { ok: true, mode: "history" };
  if (transcript.status === "success") {
    onPhase?.("outputting");
    try { outputResult = await output.output(text, outputMode); } catch (error) { outputResult = { ok: false, reason: error.message }; }
    if (outputMode === "active-window" && !outputResult?.ok) {
      const activeWindowFailure = outputResult?.reason || "active-window-output-failed";
      try {
        const fallback = await output.output(text, "clipboard");
        outputResult = fallback?.ok ? { ...fallback, fallbackFrom: "active-window", reason: activeWindowFailure } : { ok: false, mode: "clipboard", fallbackFrom: "active-window", reason: fallback?.reason || activeWindowFailure };
      } catch (error) {
        outputResult = { ok: false, mode: "clipboard", fallbackFrom: "active-window", reason: error.message || activeWindowFailure };
      }
    }
  }
  return { text, transcript, organized, history, output: outputResult };
}
