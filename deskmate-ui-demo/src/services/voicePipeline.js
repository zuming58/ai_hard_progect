export async function processVoiceRecording({ blob, stt, organizer, organizerOptions, saveHistory, output, outputMode = "history", signal }) {
  let transcript;
  try { transcript = await stt.transcribe(blob, { signal }); } catch (error) { transcript = { status: "error", text: "", provider: "unknown", durationMs: 0, message: error.message }; }
  let organized = null;
  if (transcript.status === "success") organized = await organizer.organize(transcript.text, organizerOptions);
  const text = organized?.text || "录音完成，等待转写服务";
  const history = await saveHistory({ text, transcript, organized });
  let outputResult = { ok: true, mode: "history" };
  if (transcript.status === "success") { try { outputResult = await output.output(text, outputMode); } catch (error) { outputResult = { ok: false, reason: error.message }; } }
  return { text, transcript, organized, history, output: outputResult };
}
