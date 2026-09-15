(function () {
  "use strict";

  function ageText(value) {
    if (!value) {
      return "";
    }
    var birth = new Date(value + "T00:00:00");
    var today = new Date();
    if (Number.isNaN(birth.getTime()) || birth > today) {
      return "";
    }
    var years = today.getFullYear() - birth.getFullYear();
    var months = today.getMonth() - birth.getMonth();
    var days = today.getDate() - birth.getDate();
    if (days < 0) {
      months -= 1;
      days += new Date(today.getFullYear(), today.getMonth(), 0).getDate();
    }
    if (months < 0) {
      years -= 1;
      months += 12;
    }
    return "العمر المحسوب: " + years + " سنة و " + months + " شهر و " + days + " يوم";
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-birthdate]").forEach(function (input) {
      var hint = document.createElement("small");
      hint.className = "help-text calculated-age";
      input.insertAdjacentElement("afterend", hint);

      function update() {
        hint.textContent = ageText(input.value);
      }

      input.addEventListener("input", update);
      input.addEventListener("change", update);
      update();
    });
  });
})();
