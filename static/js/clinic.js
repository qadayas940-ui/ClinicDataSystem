// سكربتات واجهة نظام العيادة
(function () {
    "use strict";

    // إخفاء رسائل التنبيه تلقائياً بعد 6 ثوانٍ
    document.addEventListener("DOMContentLoaded", function () {
        const alerts = document.querySelectorAll(".alert-dismissible");
        alerts.forEach(function (alert) {
            setTimeout(function () {
                try {
                    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                    bsAlert.close();
                } catch (e) { /* تجاهل */ }
            }, 6000);
        });
    });
})();
