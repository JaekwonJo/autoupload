(function() {
  const selectors = [
    "button[data-testid*='submit']",
    "button[data-testid*='send']",
    "button[aria-label*='Submit']",
    "button[aria-label*='Send']",
    "button[aria-label*='Create']",
    "button[type='submit']",
    "button[class*='submit']",
    "button[class*='send']",
    "[data-testid*='Submit']",
    "[data-testid*='send']"
  ];
  for (const selector of selectors) {
    const btn = document.querySelector(selector);
    if (btn) {
      btn.scrollIntoView({behavior: 'instant', block: 'center'});
      btn.click();
      return true;
    }
  }
  const arrow = document.querySelector("button svg[aria-hidden='true']");
  if (arrow && arrow.closest('button')) {
    const btn = arrow.closest('button');
    btn.scrollIntoView({behavior: 'instant', block: 'center'});
    btn.click();
    return true;
  }
  return false;
})();
