(function () {
  "use strict";

  function ageText(value) {
    if (!value) return "";
    var birth = new Date(value + "T00:00:00");
    var today = new Date();
    if (Number.isNaN(birth.getTime()) || birth > today) return "";
    var years = today.getFullYear() - birth.getFullYear();
    var months = today.getMonth() - birth.getMonth();
    var days = today.getDate() - birth.getDate();
    if (days < 0) { months -= 1; days += new Date(today.getFullYear(), today.getMonth(), 0).getDate(); }
    if (months < 0) { years -= 1; months += 12; }
    return "العمر المحسوب: " + years + " سنة و " + months + " شهر و " + days + " يوم";
  }

  function setupImport() {
    var form = document.querySelector("[data-import-form]");
    var zone = document.querySelector("[data-drop-zone]");
    if (!form || !zone) return;
    var input = zone.querySelector("input[type=file]");
    var title = zone.querySelector("[data-upload-title]");
    var subtitle = zone.querySelector("[data-upload-subtitle]");
    var progress = form.querySelector("[data-analysis-progress]");
    var bar = form.querySelector("[data-progress-bar]");
    var value = form.querySelector("[data-progress-value]");
    function selected() {
      if (input.files && input.files[0]) {
        title.textContent = input.files[0].name;
        subtitle.textContent = "تم اختيار الملف. اضغط رفع وتحليل الملف بالكامل للبدء.";
      }
    }
    input.addEventListener("change", selected);
    ["dragenter", "dragover"].forEach(function (name) { zone.addEventListener(name, function (event) { event.preventDefault(); zone.classList.add("is-dragging"); }); });
    ["dragleave", "drop"].forEach(function (name) { zone.addEventListener(name, function (event) { event.preventDefault(); zone.classList.remove("is-dragging"); }); });
    zone.addEventListener("drop", function (event) { if (event.dataTransfer.files.length) { input.files = event.dataTransfer.files; selected(); } });
    form.addEventListener("submit", function () {
      if (!input.files.length) return;
      progress.hidden = false;
      var percent = 1;
      bar.style.width = percent + "%";
      var timer = setInterval(function () {
        percent = Math.min(percent + Math.max(1, Math.round((96 - percent) / 12)), 96);
        bar.style.width = percent + "%";
        value.textContent = percent + "%";
        if (percent >= 96) clearInterval(timer);
      }, 450);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.documentElement.removeAttribute("data-theme");
    localStorage.removeItem("clinic-theme");
    document.querySelectorAll("[data-birthdate]").forEach(function (input) {
      var hint = document.createElement("small");
      hint.className = "help-text calculated-age";
      input.insertAdjacentElement("afterend", hint);
      var ageField = document.querySelector('[data-field="approx_age_value"]');
      var unitField = document.querySelector('[data-field="approx_age_unit"]');
      function update() {
        hint.textContent = ageText(input.value);
        [ageField, unitField].forEach(function (field) {
          if (!field) return;
          field.hidden = Boolean(input.value);
          if (input.value) {
            var control = field.querySelector("input, select");
            if (control) control.value = "";
          }
        });
      }
      input.addEventListener("input", update);
      input.addEventListener("change", update);
      update();
    });
    setupImport();
  });
})();
