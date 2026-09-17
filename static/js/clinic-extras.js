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
          if (doctor._comboRefresh) doctor._comboRefresh();
        })
        .finally(function () { doctor.disabled = false; });
    });
  }

  function setupSearchableComboboxes(root) {
    root.querySelectorAll("select[data-searchable-combobox]").forEach(function(select){
      if (select.dataset.comboReady) return;
      select.dataset.comboReady = "1";
      var wrapper=document.createElement("div"), input=document.createElement("input"), button=document.createElement("button"), menu=document.createElement("div");
      wrapper.className="searchable-combobox"; input.type="text"; input.className="form-control"; input.autocomplete="off";
      button.type="button"; button.className="combo-arrow"; button.setAttribute("aria-label","فتح الخيارات"); button.textContent="⌄";
      menu.className="combo-menu"; menu.hidden=true;
      select.parentNode.insertBefore(wrapper,select); wrapper.appendChild(input); wrapper.appendChild(button); wrapper.appendChild(menu); wrapper.appendChild(select); select.classList.add("combo-native");
      function options(){return Array.from(select.options).filter(function(option){return option.value;});}
      function selectedText(){var option=select.options[select.selectedIndex];return option&&option.value?option.text:"";}
      function render(query){var normalized=(query||"").trim().toLowerCase();var items=options().filter(function(option){return !normalized||option.text.toLowerCase().indexOf(normalized)>=0;});menu.innerHTML=items.length?items.map(function(option){return '<button type="button" data-value="'+escapeHtml(option.value)+'">'+escapeHtml(option.text)+'</button>';}).join(""):'<span>لا توجد نتائج</span>';menu.hidden=false;menu.querySelectorAll("button").forEach(function(item){item.addEventListener("click",function(){select.value=item.dataset.value;input.value=selectedText();menu.hidden=true;select.dispatchEvent(new Event("change",{bubbles:true}));});});}
      input.value=selectedText(); input.addEventListener("input",function(){render(input.value);}); input.addEventListener("focus",function(){render(input.value);}); button.addEventListener("click",function(){if(menu.hidden)render("");else menu.hidden=true;});
      select.addEventListener("change",function(){input.value=selectedText();});
      select._comboRefresh=function(){input.value=selectedText();if(!menu.hidden)render(input.value);};
      document.addEventListener("click",function(event){if(!wrapper.contains(event.target))menu.hidden=true;});
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
      setupBirthdate(drawer); setupSearchableComboboxes(drawer); setupDepartmentDoctors(drawer);
      var form=drawer.querySelector("[data-drawer-form]"); if(!form)return;
      form.addEventListener("submit",function(event){event.preventDefault();var submit=form.querySelector('[type="submit"]');if(submit)submit.disabled=true;fetch(form.action,{method:"POST",body:new FormData(form),headers:{"X-Requested-With":"XMLHttpRequest"}}).then(function(response){var type=response.headers.get("content-type")||"";if(type.indexOf("application/json")>=0)return response.json();return response.text().then(function(html){throw {html:html};});}).then(function(data){var row=screen.querySelector('[data-drawer-url="'+form.action+'"]');if(row&&data.patient){var name=row.querySelector("[data-row-name]");if(name)name.textContent=data.patient.name;}var message=drawer.querySelector("[data-drawer-message]");if(message){message.hidden=false;message.className="drawer-message success";message.textContent=data.message;}setTimeout(closeDrawer,700);}).catch(function(error){if(error.html){drawer.innerHTML=error.html;wireDrawer();}else{var message=drawer.querySelector("[data-drawer-message]");if(message){message.hidden=false;message.textContent="تعذر حفظ التغييرات. تحقق من الحقول وحاول مرة أخرى.";}}}).finally(function(){if(submit)submit.disabled=false;});});
    }
    function openDrawer(url){drawer.hidden=false;drawer.innerHTML='<div class="drawer-loading">جارٍ فتح بطاقة المريض…</div>';screen.classList.add("drawer-open");fetch(url,{headers:{"X-Requested-With":"XMLHttpRequest"}}).then(function(r){return r.text();}).then(function(html){drawer.innerHTML=html;wireDrawer();}).catch(function(){drawer.innerHTML='<div class="alert alert-danger">تعذر فتح بطاقة المريض.</div>';});}
    screen.querySelectorAll("[data-patient-row]").forEach(function(row){row.addEventListener("dblclick",function(event){if(event.target.closest("a,button,input,select,textarea"))return;openDrawer(row.dataset.drawerUrl);});var button=row.querySelector("[data-open-drawer]");if(button)button.addEventListener("click",function(){openDrawer(row.dataset.drawerUrl);});});
    var initial=screen.dataset.initialPatient;if(initial){var row=screen.querySelector('[data-drawer-url*="'+initial+'"]');if(row)openDrawer(row.dataset.drawerUrl);}
  }

  function setupPatientChanges() {
    var screen=document.querySelector("[data-patient-screen]"), notice=document.querySelector("[data-change-notice]");
    if(!screen||!notice||!screen.dataset.changesUrl)return;
    notice.addEventListener("click",function(){window.location.reload();});
    window.setInterval(function(){
      if(document.hidden||!document.body.contains(screen))return;
      fetch(screen.dataset.changesUrl+"?token="+encodeURIComponent(screen.dataset.changeToken),{headers:{"X-Requested-With":"XMLHttpRequest"}})
        .then(function(r){return r.json();}).then(function(data){if(data.changed)notice.hidden=false;}).catch(function(){});
    },15000);
  }

  function setupNotifications() {
    var button = document.querySelector("[data-notification-button]");
    var badge = document.querySelector("[data-notification-badge]");
    function setCount(count) {
      if (!badge) return;
      badge.textContent = count;
      badge.hidden = !count;
    }
    function csrfToken() {
      var input = document.querySelector('[name="csrfmiddlewaretoken"]');
      if (input) return input.value;
      var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : "";
    }
    document.querySelectorAll("[data-notification-open]").forEach(function(link){
      link.addEventListener("click", function(event){
        event.preventDefault();
        fetch(link.href, {method:"POST",headers:{"X-Requested-With":"XMLHttpRequest","X-CSRFToken":csrfToken()}})
          .then(function(response){ return response.json(); })
          .then(function(data){ link.classList.remove("unread"); setCount(data.unread); window.location.href = data.target_url; })
          .catch(function(){ window.location.href = link.href; });
      });
    });
    var markAll = document.querySelector("[data-mark-all-read]");
    if (markAll) markAll.addEventListener("submit", function(event){
      event.preventDefault();
      fetch(markAll.action || window.location.href, {method:"POST",body:new FormData(markAll),headers:{"X-Requested-With":"XMLHttpRequest"}})
        .then(function(response){ return response.json(); }).then(function(data){
          document.querySelectorAll(".notification-item.unread").forEach(function(item){ item.classList.remove("unread"); });
          setCount(data.unread);
        });
    });
    if (button && button.dataset.statusUrl) window.setInterval(function(){
      if (document.hidden) return;
      fetch(button.dataset.statusUrl, {headers:{"X-Requested-With":"XMLHttpRequest"}})
        .then(function(response){ return response.json(); }).then(function(data){ setCount(data.unread); }).catch(function(){});
    }, 15000);
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>\"']/g, function (character) {
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;","'":"&#39;"}[character];
    });
  }

  function setupLivePatientSearch(root) {
    root.querySelectorAll("[data-live-patient-search]").forEach(function(input){
      if (input.dataset.liveReady) return;
      input.dataset.liveReady = "1";
      var form = input.closest("form");
      var box = document.createElement("div");
      box.className = "live-search-results";
      box.hidden = true;
      (form || input.parentElement).appendChild(box);
      var timer = null;
      input.addEventListener("input", function(){
        window.clearTimeout(timer);
        var query = input.value.trim();
        if (!query) { box.hidden = true; box.innerHTML = ""; return; }
        timer = window.setTimeout(function(){
          fetch(input.dataset.searchUrl + "?q=" + encodeURIComponent(query), {headers:{"X-Requested-With":"XMLHttpRequest"}})
            .then(function(response){ return response.json(); })
            .then(function(data){
              if (!data.results.length) { box.hidden = false; box.innerHTML = '<div class="live-search-empty">لا يوجد مريض مطابق</div>'; return; }
              box.hidden = false;
              box.innerHTML = data.results.map(function(item){
                return '<a href="' + escapeHtml(item.url) + '"><span class="patient-avatar ' + escapeHtml(item.gender) + '">●</span><span><b>' + escapeHtml(item.name) + '</b><small>' + escapeHtml(item.code) + ' · ' + escapeHtml(item.phone) + ' · ' + escapeHtml(item.age) + '</small></span></a>';
              }).join("");
            }).catch(function(){ box.hidden = true; });
        }, 280);
      });
      document.addEventListener("click", function(event){ if (!box.contains(event.target) && event.target !== input) box.hidden = true; });
    });
  }

  function setupPatientMatcher(root) {
    var name = root.querySelector("[data-patient-match-name]");
    if (!name) return;
    var form = name.closest("form");
    if (!form || form.dataset.patientMatcherReady || form.hasAttribute("data-drawer-form")) return;
    form.dataset.patientMatcherReady = "1";
    var phone = form.querySelector("[data-patient-match-phone]");
    var age = form.querySelector("[data-patient-match-age]");
    var birthDate = form.querySelector('[name="date_of_birth"]');
    var gender = form.querySelector('[name="gender"]');
    var address = form.querySelector('[name="address"]');
    var results = document.createElement("section");
    results.className = "patient-match-results";
    results.hidden = true;
    var actions = form.querySelector(".form-actions");
    if (actions) form.insertBefore(results, actions); else form.appendChild(results);
    var timer = null;

    function search() {
      var values = {
        name: name.value.trim(), phone: phone ? phone.value.trim() : "", age: age ? age.value.trim() : "",
        birth_date: birthDate ? birthDate.value : "", gender: gender ? gender.value : "", address: address ? address.value.trim() : ""
      };
      var usefulName = values.name.split(/\s+/).filter(Boolean).length >= 2;
      if (!usefulName && values.phone.replace(/\D/g, "").length < 7 && !values.birth_date) {
        results.hidden = true; results.innerHTML = ""; return;
      }
      fetch("/patients/api/match/?" + new URLSearchParams(values).toString(), {headers:{"X-Requested-With":"XMLHttpRequest"}})
        .then(function(response){ return response.json(); })
        .then(function(data){
          if (!data.results.length) { results.hidden = true; results.innerHTML = ""; return; }
          results.hidden = false;
          results.innerHTML = '<div class="match-title"><b>تم العثور على ملف/ملفات محتملة لهذا المريض</b><span>تحقق من البيانات مع المريض. المطابقة لا تدمج أي سجل تلقائياً.</span></div>' + data.results.map(function(item){
            return '<article class="duplicate-candidate-card"><div><b>' + escapeHtml(item.name) + '</b><small>' + escapeHtml(item.code) + ' · ' + escapeHtml(item.gender) + ' · ' + escapeHtml(item.age) + '</small><small>' + escapeHtml(item.phone) + ' · ' + escapeHtml(item.address) + '</small><small>القسم: ' + escapeHtml(item.department) + (item.last_visit ? ' · آخر زيارة: ' + escapeHtml(item.last_visit) : '') + '</small><small>سبب المطابقة: ' + escapeHtml(item.reasons.join("، ")) + '</small></div><div class="candidate-actions"><a class="btn btn-outline" href="' + escapeHtml(item.edit_url) + '">فتح الملف وتعديل المعلومات</a><a class="btn btn-primary" href="' + escapeHtml(item.visit_url) + '">تأكيد المريض وإضافة زيارة</a><button class="btn btn-secondary" type="button" data-new-patient>مريض لأول مرة — تسجيل جديد</button></div></article>';
          }).join("");
          results.querySelectorAll("[data-new-patient]").forEach(function(button){ button.addEventListener("click", function(){
            var override = form.querySelector('[name="duplicate_override"]');
            if (!override) { override = document.createElement("input"); override.type = "hidden"; override.name = "duplicate_override"; form.appendChild(override); }
            override.value = "1"; results.hidden = true;
          }); });
        }).catch(function(){ results.hidden = true; });
    }

    [name, phone, age, birthDate, gender, address].filter(Boolean).forEach(function(input){
      input.addEventListener("input", function(){ window.clearTimeout(timer); timer = window.setTimeout(search, 420); });
      input.addEventListener("change", function(){ window.clearTimeout(timer); search(); });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.documentElement.removeAttribute("data-theme"); localStorage.removeItem("clinic-theme");
    setupBirthdate(document); setupSearchableComboboxes(document); setupDepartmentDoctors(document); setupImport(); setupDrawer(); setupPatientChanges(); setupNotifications(); setupLivePatientSearch(document); setupPatientMatcher(document);
    document.querySelectorAll("[data-auto-submit]").forEach(function(item){item.addEventListener("change",function(){item.form.submit();});});
    document.querySelectorAll("[data-global-back]").forEach(function(button){button.addEventListener("click",function(){if(window.history.length>1){window.history.back();}else{window.location.href=button.dataset.fallbackUrl||"/";}});});
  });
})();
