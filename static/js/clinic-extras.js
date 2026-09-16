(function () {
  "use strict";

  function ageText(value) {
    if (!value) return "";
    var birth = new Date(value + "T00:00:00"), today = new Date();
    if (Number.isNaN(birth.getTime()) || birth > today) return "";
    var years = today.getFullYear() - birth.getFullYear();
    var months = today.getMonth() - birth.getMonth();
    var days = today.getDate() - birth.getDate();
    if (days < 0) { months -= 1; days += new Date(today.getFullYear(), today.getMonth(), 0).getDate(); }
    if (months < 0) { years -= 1; months += 12; }
    return "العمر المحسوب: " + years + " سنة و " + months + " شهر و " + days + " يوم";
  }

  function setupBirthdate(root) {
    root.querySelectorAll("[data-birthdate]").forEach(function (input) {
      if (input.dataset.ready) return;
      input.dataset.ready = "1";
      var hint = document.createElement("small");
      hint.className = "help-text calculated-age";
      input.insertAdjacentElement("afterend", hint);
      var scope = input.closest("form") || root;
      var ageField = scope.querySelector('[data-field="approx_age_value"]');
      var unitField = scope.querySelector('[data-field="approx_age_unit"]');
      var ageOutput = scope.querySelector("[data-calculated-age]");
      function update() {
        hint.textContent = ageText(input.value);
        if (ageOutput && input.value) ageOutput.value = ageText(input.value).replace("العمر المحسوب: ", "");
        if (ageOutput && !input.value) {
          var approximate = ageField && ageField.querySelector("input");
          var unit = unitField && unitField.querySelector("select");
          ageOutput.value = approximate && approximate.value ? approximate.value + " " + (unit && unit.options[unit.selectedIndex] ? unit.options[unit.selectedIndex].text : "") : "غير محدد";
        }
        [ageField, unitField].forEach(function (field) {
          if (!field) return;
          field.hidden = Boolean(input.value);
          var control = field.querySelector("input, select");
          if (input.value && control) control.value = "";
        });
      }
      input.addEventListener("input", update); input.addEventListener("change", update); update();
      [ageField, unitField].forEach(function(field){ if(!field)return; var control=field.querySelector("input,select"); if(control){control.addEventListener("input",update);control.addEventListener("change",update);} });
    });
  }

  function setupDepartmentDoctors(root) {
    var department = root.querySelector("[data-department-select]");
    var doctor = root.querySelector("[data-doctor-select]");
    if (!department || !doctor || department.dataset.ready) return;
    department.dataset.ready = "1";
    department.addEventListener("change", function () {
      doctor.disabled = true;
      fetch("/patients/api/doctors/?department=" + encodeURIComponent(department.value), {headers:{"X-Requested-With":"XMLHttpRequest"}})
        .then(function (response) { return response.json(); })
        .then(function (data) {
          doctor.innerHTML = '<option value="">— اختر الطبيب —</option>';
          data.results.forEach(function (item) { var option = document.createElement("option"); option.value = item.id; option.textContent = item.text; doctor.appendChild(option); });
        })
        .finally(function () { doctor.disabled = false; });
    });
  }

  function setupImport() {
    var form = document.querySelector("[data-import-form]"), zone = document.querySelector("[data-drop-zone]");
    if (!form || !zone) return;
    var input = zone.querySelector("input[type=file]"), title = zone.querySelector("[data-upload-title]"), subtitle = zone.querySelector("[data-upload-subtitle]");
    var progress = form.querySelector("[data-analysis-progress]"), bar = form.querySelector("[data-progress-bar]"), value = form.querySelector("[data-progress-value]");
    function selected() { if (input.files && input.files[0]) { title.textContent = input.files[0].name; subtitle.textContent = "تم اختيار الملف. اضغط رفع وتحليل الملف الكامل للبدء."; } }
    input.addEventListener("change", selected);
    ["dragenter","dragover"].forEach(function (name) { zone.addEventListener(name,function(e){e.preventDefault();zone.classList.add("is-dragging");}); });
    ["dragleave","drop"].forEach(function (name) { zone.addEventListener(name,function(e){e.preventDefault();zone.classList.remove("is-dragging");}); });
    zone.addEventListener("drop",function(e){if(e.dataTransfer.files.length){input.files=e.dataTransfer.files;selected();}});
    form.addEventListener("submit",function(){if(!input.files.length)return;progress.hidden=false;var percent=1;var timer=setInterval(function(){percent=Math.min(percent+Math.max(1,Math.round((96-percent)/12)),96);bar.style.width=percent+"%";value.textContent=percent+"%";if(percent>=96)clearInterval(timer);},450);});
  }

  function setupDrawer() {
    var screen = document.querySelector("[data-patient-screen]"); if (!screen) return;
    var drawer = screen.querySelector("[data-patient-drawer]");
    function closeDrawer(){drawer.hidden=true;drawer.innerHTML="";screen.classList.remove("drawer-open");}
    function wireDrawer(){
      drawer.querySelectorAll("[data-close-drawer]").forEach(function(button){button.addEventListener("click",closeDrawer);});
      setupBirthdate(drawer); setupDepartmentDoctors(drawer);
      var form=drawer.querySelector("[data-drawer-form]"); if(!form)return;
      form.addEventListener("submit",function(event){event.preventDefault();var submit=form.querySelector('[type="submit"]');if(submit)submit.disabled=true;fetch(form.action,{method:"POST",body:new FormData(form),headers:{"X-Requested-With":"XMLHttpRequest"}}).then(function(response){var type=response.headers.get("content-type")||"";if(type.indexOf("application/json")>=0)return response.json();return response.text().then(function(html){throw {html:html};});}).then(function(data){var row=screen.querySelector('[data-drawer-url="'+form.action+'"]');if(row&&data.patient){var name=row.querySelector("[data-row-name]");if(name)name.textContent=data.patient.name;}var message=drawer.querySelector("[data-drawer-message]");if(message){message.hidden=false;message.className="drawer-message success";message.textContent=data.message;}setTimeout(closeDrawer,700);}).catch(function(error){if(error.html){drawer.innerHTML=error.html;wireDrawer();}else{var message=drawer.querySelector("[data-drawer-message]");if(message){message.hidden=false;message.textContent="تعذر حفظ التغييرات. تحقق من الحقول وحاول مرة أخرى.";}}}).finally(function(){if(submit)submit.disabled=false;});});
    }
    function openDrawer(url){drawer.hidden=false;drawer.innerHTML='<div class="drawer-loading">جارٍ فتح بطاقة المريض…</div>';screen.classList.add("drawer-open");fetch(url,{headers:{"X-Requested-With":"XMLHttpRequest"}}).then(function(r){return r.text();}).then(function(html){drawer.innerHTML=html;wireDrawer();}).catch(function(){drawer.innerHTML='<div class="alert alert-danger">تعذر فتح بطاقة المريض.</div>';});}
    screen.querySelectorAll("[data-patient-row]").forEach(function(row){row.addEventListener("dblclick",function(event){if(event.target.closest("a,button,input,select,textarea"))return;openDrawer(row.dataset.drawerUrl);});var button=row.querySelector("[data-open-drawer]");if(button)button.addEventListener("click",function(){openDrawer(row.dataset.drawerUrl);});});
    var initial=screen.dataset.initialPatient;if(initial){var row=screen.querySelector('[data-drawer-url*="'+initial+'"]');if(row)openDrawer(row.dataset.drawerUrl);}
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.documentElement.removeAttribute("data-theme"); localStorage.removeItem("clinic-theme");
    setupBirthdate(document); setupDepartmentDoctors(document); setupImport(); setupDrawer();
    document.querySelectorAll("[data-auto-submit]").forEach(function(item){item.addEventListener("change",function(){item.form.submit();});});
  });
})();
