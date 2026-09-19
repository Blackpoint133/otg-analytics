"""Global public-site beta status and donation bar."""

import streamlit as st
import streamlit.components.v1 as components


EVM_DONATION_WALLET = "0x956cff3a596AD30D6A767DfFc3F70CDE97CD2667"


def render_global_status_bar() -> None:
    """Render the fixed public status bar and its small browser wiring."""
    st.markdown(
        f"""
<style>
:root{{--otg-status-bar-left:0px;--otg-status-bar-height:32px}}
.otg-global-status-bar{{position:fixed;left:var(--otg-status-bar-left);right:0;bottom:0;height:var(--otg-status-bar-height);box-sizing:border-box;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:0 16px;background:#050607;border-top:1px solid #26292d;color:#aeb3ba;font-family:'PP Supply Sans','Space Mono',monospace,sans-serif;font-size:10px;font-weight:600;line-height:1;letter-spacing:.7px;text-transform:uppercase;z-index:2147482000}}
.otg-status-beta{{color:#858b93}}
.otg-status-donation{{display:inline-flex;align-items:center;justify-content:flex-end;gap:10px;min-width:0}}
.otg-status-copy{{display:inline-flex;align-items:center;gap:10px;min-width:0;margin:0;padding:0;background:transparent;border:0;border-radius:0;color:#e1e3e6;font:inherit;letter-spacing:inherit;text-transform:inherit;cursor:pointer;white-space:nowrap}}
.otg-status-copy:hover,.otg-status-copy:focus-visible{{color:#ff003a;outline:none}}
.otg-status-wallet-label{{color:#737981}}
.otg-status-mobile{{display:none}}
[data-testid="stMainBlockContainer"]{{padding-bottom:calc(var(--otg-status-bar-height) + 12px)!important}}
@media(max-width:768px){{:root{{--otg-status-bar-left:0px!important;--otg-status-bar-height:30px}}.otg-global-status-bar{{left:0!important;gap:8px;padding:0 10px;font-size:9px;letter-spacing:.5px}}.otg-status-desktop{{display:none}}.otg-status-mobile{{display:inline}}.otg-status-donation,.otg-status-copy{{gap:6px}}}}
@media(max-width:380px){{.otg-global-status-bar{{padding:0 8px;font-size:8px;letter-spacing:.3px}}.otg-status-donation,.otg-status-copy{{gap:4px}}}}
</style>
<div class="otg-global-status-bar" role="status" aria-label="OTG Analytics beta status">
  <span class="otg-status-desktop">OTG ANALYTICS // <span class="otg-status-beta">BETA</span></span>
  <span class="otg-status-mobile otg-status-beta">BETA</span>
  <span class="otg-status-donation">
    <span class="otg-status-desktop">&#9749; Buy me a coffee?</span>
    <button type="button" class="otg-status-copy" data-wallet="{EVM_DONATION_WALLET}" aria-label="Copy EVM donation wallet address">
      <span class="otg-status-desktop otg-status-copy-value">{EVM_DONATION_WALLET}</span>
      <span class="otg-status-mobile otg-status-copy-value">&#9749; 0x956c&hellip;2667</span>
      <span class="otg-status-wallet-label"><span class="otg-status-desktop">EVM ADDRESS</span><span class="otg-status-mobile">EVM</span></span>
    </button>
  </span>
</div>
""",
        unsafe_allow_html=True,
    )
    components.html(
        """
<script>
(function () {
  var win = window.parent;
  var doc;
  try { doc = win.document; } catch (error) { return; }
  var stateKey = '__otgGlobalStatusBarState';
  var prior = win[stateKey];
  if (prior && prior.destroy) prior.destroy();
  var resizeObserver = null;
  var mutationObserver = null;
  var copyTimer = null;

  function updateSidebarOffset() {
    var sidebar = doc.querySelector('[data-testid="stSidebar"]');
    var offset = 0;
    if (sidebar && win.innerWidth > 768) {
      var rect = sidebar.getBoundingClientRect();
      var style = win.getComputedStyle(sidebar);
      if (style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.right > 0) {
        offset = Math.max(0, Math.min(win.innerWidth, rect.right));
      }
    }
    doc.documentElement.style.setProperty('--otg-status-bar-left', offset + 'px');
  }

  function legacyCopy(value) {
    var textarea = doc.createElement('textarea');
    textarea.value = value;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    doc.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    var copied = false;
    try { copied = doc.execCommand('copy'); }
    finally { doc.body.removeChild(textarea); }
    return copied;
  }

  function setCopyState(button, copied) {
    var values = button.querySelectorAll('.otg-status-copy-value');
    values.forEach(function (node) {
      if (!node.dataset.normalText) node.dataset.normalText = node.textContent;
      node.textContent = copied ? 'COPIED' : node.dataset.normalText;
    });
  }

  function onClick(event) {
    var button = event.target.closest('.otg-status-copy[data-wallet]');
    if (!button) return;
    var wallet = button.dataset.wallet;
    var clipboard = win.navigator && win.navigator.clipboard;
    var primary = clipboard && clipboard.writeText;
    var write = primary ? primary.call(clipboard, wallet).then(function () { return true; }).catch(function () { return legacyCopy(wallet); }) : Promise.resolve(legacyCopy(wallet));
    write.then(function (copied) {
      if (!copied) return;
      setCopyState(button, true);
      if (copyTimer) win.clearTimeout(copyTimer);
      copyTimer = win.setTimeout(function () { setCopyState(button, false); }, 1300);
    });
  }

  function destroy() {
    win.removeEventListener('resize', updateSidebarOffset);
    doc.removeEventListener('click', onClick);
    if (resizeObserver) resizeObserver.disconnect();
    if (mutationObserver) mutationObserver.disconnect();
    if (copyTimer) win.clearTimeout(copyTimer);
    doc.documentElement.style.removeProperty('--otg-status-bar-left');
    delete win[stateKey];
  }

  win.addEventListener('resize', updateSidebarOffset);
  doc.addEventListener('click', onClick);
  if (win.ResizeObserver) {
    resizeObserver = new win.ResizeObserver(updateSidebarOffset);
    var sidebar = doc.querySelector('[data-testid="stSidebar"]');
    if (sidebar) resizeObserver.observe(sidebar);
  }
  mutationObserver = new win.MutationObserver(updateSidebarOffset);
  mutationObserver.observe(doc.body, {subtree:true, childList:true, attributes:true, attributeFilter:['style','class','aria-expanded']});
  updateSidebarOffset();
  win[stateKey] = {destroy:destroy};
})();
</script>
""",
        height=0,
        width=0,
    )

