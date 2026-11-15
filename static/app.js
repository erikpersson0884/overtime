(function () {
  // Prefill today's date from the phone's own clock (not the server's).
  var dateInput = document.querySelector("input[data-today]");
  if (dateInput) {
    var d = new Date();
    var pad = function (n) { return String(n).padStart(2, "0"); };
    dateInput.value = d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  // Live total: hours (decimals ok) + minutes (can exceed 59).
  var hours = document.getElementById("hours");
  var minutes = document.getElementById("minutes");
  var total = document.getElementById("total");

  function num(v) {
    v = (v || "").trim().replace(",", ".");
    if (v === "") return 0;
    var n = Number(v);
    return isFinite(n) && n >= 0 ? n : NaN;
  }
  function fmt(m) {
    var h = Math.floor(m / 60), r = m % 60;
    if (h && r) return h + "h " + r + "m";
    if (h) return h + "h";
    return r + "m";
  }
  function update() {
    var h = num(hours.value), m = num(minutes.value);
    if (isNaN(h) || isNaN(m)) { total.textContent = "Check the numbers"; return; }
    total.textContent = fmt(Math.floor(h * 60 + m + 0.5));
  }
  if (hours && minutes && total) {
    hours.addEventListener("input", update);
    minutes.addEventListener("input", update);
    update();
  }

  // Confirm before deleting.
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.getAttribute("data-confirm"))) e.preventDefault();
    });
  });
})();
