// Log simple visible dentro del panel (no solo consola de desarrollador).
function logToPanel(message, isError) {
  const list = document.getElementById("log-list");
  if (!list) return;
  const entry = document.createElement("div");
  entry.textContent = (isError ? "[ERROR] " : "") + message;
  entry.style.color = isError ? "#e06c75" : "inherit";
  list.prepend(entry);
}
