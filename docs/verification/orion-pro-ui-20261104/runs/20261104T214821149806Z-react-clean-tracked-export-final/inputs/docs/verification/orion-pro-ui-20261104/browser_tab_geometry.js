async (page) => page.evaluate(() => {
  const tablist = document.querySelector('[role="tablist"][aria-label="Analyse du match"]');
  const selected = tablist?.querySelector('[role="tab"][aria-selected="true"]');
  if (!tablist || !selected) throw Error("Selected analysis tab missing");
  const rect = (element) => {
    const r = element.getBoundingClientRect();
    return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
  };
  const list = rect(tablist), active = rect(selected);
  const clip = {
    left: Math.max(0, list.left + tablist.clientLeft),
    right: Math.min(innerWidth, list.left + tablist.clientLeft + tablist.clientWidth),
    top: Math.max(0, list.top + tablist.clientTop),
    bottom: Math.min(innerHeight, list.top + tablist.clientTop + tablist.clientHeight),
  };
  return {
    selected: selected.textContent.trim(), ariaSelected: selected.getAttribute("aria-selected"),
    list, active, clip, scrollLeft: tablist.scrollLeft, clientWidth: tablist.clientWidth, scrollWidth: tablist.scrollWidth,
    viewport: { width: innerWidth, height: innerHeight }, documentScroll: { x: scrollX, y: scrollY },
    fullyWithinHorizontalScrollport: active.left >= clip.left - 1 && active.right <= clip.right + 1,
    fullyWithinVerticalScrollport: active.top >= clip.top - 1 && active.bottom <= clip.bottom + 1,
  };
})
