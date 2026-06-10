(function () {
  const otpInputContainer = document.querySelector("[data-otp-input]");
  const digitsContainer = document.querySelector("[data-otp-digits]");
  const tokenInput = document.getElementById("id_otp_token");

  if (!otpInputContainer || !digitsContainer || !tokenInput) {
    return;
  }

  const digitInputs = Array.from(
    digitsContainer.querySelectorAll(".otp-tunnel-otp-digits__input")
  );

  function syncHiddenInput() {
    tokenInput.value = digitInputs.map((input) => input.value).join("");
  }

  function fillDigitsFromValue(value) {
    const digits = value.replace(/\D/g, "").slice(0, digitInputs.length);
    digitInputs.forEach((input, index) => {
      input.value = digits[index] || "";
    });
    syncHiddenInput();
  }

  otpInputContainer.classList.add("otp-tunnel-otp-input--enhanced");
  digitsContainer.hidden = false;
  fillDigitsFromValue(tokenInput.value);
  digitInputs.forEach((input) => {
    input.tabIndex = 0;
  });
  digitInputs[0].focus();

  digitInputs.forEach((input, index) => {
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "").slice(-1);
      syncHiddenInput();

      if (input.value && index < digitInputs.length - 1) {
        digitInputs[index + 1].focus();
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && !input.value && index > 0) {
        digitInputs[index - 1].focus();
      }
    });

    input.addEventListener("paste", (event) => {
      event.preventDefault();
      const pasted = (event.clipboardData || window.clipboardData).getData("text");
      fillDigitsFromValue(pasted);

      const nextEmptyIndex = digitInputs.findIndex((digitInput) => !digitInput.value);
      const focusIndex =
        nextEmptyIndex === -1 ? digitInputs.length - 1 : nextEmptyIndex;
      digitInputs[focusIndex].focus();
    });
  });
})();
