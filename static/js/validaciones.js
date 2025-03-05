document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll(".needs-validation");

    forms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });

    // Validación en tiempo real para la cédula
    document.getElementById("cedula").addEventListener("input", function () {
        this.value = this.value.replace(/\D/g, "").slice(0, 10); // Solo números, máximo 10 caracteres
    });

    // Validación en tiempo real para el nombre
    document.getElementById("nombre").addEventListener("input", function () {
        this.value = this.value.replace(/[^A-Za-zÁÉÍÓÚáéíóúñÑ ]/g, ""); // Solo letras y espacios
    });
});
