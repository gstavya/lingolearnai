document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("login-form");
    const googleLoginButton = document.getElementById("google-login");
    const logoutButton = document.getElementById("logout");

    // Firebase configuration
    const firebaseConfig = {
        apiKey: "AIzaSyDdoS-DHFQvbr2BS5VfxfAr7iJSoUpFOvg",
        authDomain: "lingolearn-ai.firebaseapp.com",
        projectId: "lingolearn-ai",
        storageBucket: "lingolearn-ai.firebasestorage.app",
        messagingSenderId: "106525674540",
        appId: "1:106525674540:web:50d8880181ddbd101d9589",
        measurementId: "G-HBCX40Z787"
      };

    // Initialize Firebase
    if (!firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
    }

    // Handle Email/Password Login
    if (loginForm) {
        loginForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;

            firebase.auth().signInWithEmailAndPassword(email, password)
                .then(userCredential => userCredential.user.getIdToken())
                .then(idToken => {
                    return fetch("/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ idToken: idToken })
                    });
                })
                .then(response => {
                    if (response.ok) {
                        window.location.href = "/dashboard";
                    } else {
                        alert("Login failed.");
                    }
                })
                .catch(error => {
                    console.error("Login Error:", error);
                    alert("Invalid email or password.");
                });
        });
    }

    // Handle Google Login
    if (googleLoginButton) {
        googleLoginButton.addEventListener("click", function () {
            const provider = new firebase.auth.GoogleAuthProvider();

            firebase.auth().signInWithPopup(provider)
                .then(result => result.user.getIdToken())
                .then(idToken => {
                    return fetch("/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ idToken: idToken })
                    });
                })
                .then(response => {
                    if (response.ok) {
                        window.location.href = "/dashboard";
                    } else {
                        alert("Google login failed.");
                    }
                })
                .catch(error => {
                    console.error("Google Login Error:", error);
                    alert("Could not sign in with Google.");
                });
        });
    }

    // Handle Logout
    if (logoutButton) {
        logoutButton.addEventListener("click", function () {
            firebase.auth().signOut()
                .then(() => {
                    return fetch("/logout", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    });
                })
                .then(() => {
                    window.location.href = "/";
                })
                .catch(error => {
                    console.error("Logout Error:", error);
                    alert("Error logging out.");
                });
        });
    }
});
