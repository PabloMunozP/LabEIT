// Test de robustez de contraseña (password strength)
function CheckPasswordStrength(elemento_password,id_elemento_robustez,id_barra_progreso,id_boton_submit) {
	password = elemento_password.value; // Valor de la contraseña en cada input de teclado
  var password_strength = document.getElementById(id_elemento_robustez);  // Elemento para mostrar info de robustez
	var progress_bar = document.getElementById(id_barra_progreso);
		//if textBox is empty
    if(password.length==0){
				progress_bar.style.width = "0%";
        password_strength.innerHTML = "";
				document.getElementById(id_boton_submit).disabled = true;
        return;
    }

    //Regular Expressions
    var regex = new Array();
    regex.push("[A-Z]"); //For Uppercase Alphabet
    regex.push("[a-z]"); //For Lowercase Alphabet
    regex.push("[0-9]"); //For Numeric Digits
    regex.push("[$@$!%*#?&]"); //For Special Characters

    var passed = 0;

    //Validation for each Regular Expression
    for (var i = 0; i < regex.length; i++) {
        if((new RegExp (regex[i])).test(password)){
            passed++;
        }
    }

    //Validation for Length of Password
    if(passed > 2 && password.length >= 8){
        passed++;
    }

    //Display of Status
		var progress_bar_percentage = 0;
    var color = "";
    var passwordStrength = "";

		// Se eliminan las clases de colores en caso de haber
		progress_bar.classList.remove("bg-success");
		progress_bar.classList.remove("bg-info");
		progress_bar.classList.remove("bg-warning");
		progress_bar.classList.remove("bg-danger");
		// Se agrega color y porcentaje según test anterior
    switch(passed){
        case 0:
            break;
        case 1:
            passwordStrength = "Bajo";
            color = "Red";
						progress_bar.style.width = "25%";
						progress_bar.classList.add("bg-danger");
            break;
        case 2:
            passwordStrength = "Medio";
            color = "darkorange";
						progress_bar.style.width = "50%";
						progress_bar.classList.add("bg-warning");
            break;
        case 3:
						passwordStrength = "Medio";
						color = "darkorange";
						progress_bar.style.width = "50%";
						progress_bar.classList.add("bg-warning");
            break;
        case 4:
            passwordStrength = "Alto";
            color = "Green";
						progress_bar.style.width = "75%";
						progress_bar.classList.add("bg-success");
            break;
        case 5:
            passwordStrength = "Muy alto";
            color = "darkgreen";
						progress_bar.style.width = "100%";
						progress_bar.classList.add("bg-success");
            break;
    }
    password_strength.innerHTML = passwordStrength;
    password_strength.style.color = color;
		if(passed >= 2){
			document.getElementById(id_boton_submit).disabled = false;
		}else{
			document.getElementById(id_boton_submit).disabled = true;
		}

	}

	/*!
	    * Start Bootstrap - SB Admin v6.0.0 (https://startbootstrap.com/templates/sb-admin)
	    * Copyright 2013-2020 Start Bootstrap
	    * Licensed under MIT (https://github.com/BlackrockDigital/startbootstrap-sb-admin/blob/master/LICENSE)
	    */
	    (function($) {
	    "use strict";

	    // Add active state to sidbar nav links
	    var path = window.location.href; // because the 'href' property of the DOM element is the absolute path
	        $("#layoutSidenav_nav .sb-sidenav a.nav-link").each(function() {
	            if (this.href === path) {
	                $(this).addClass("active");
	            }
	        });

	    // Toggle the side navigation
	    $("#sidebarToggle").on("click", function(e) {
	        e.preventDefault();
	        $("body").toggleClass("sb-sidenav-toggled");
	    });
	})(jQuery);
