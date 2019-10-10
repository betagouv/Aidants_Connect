function showContactMethod() {
  const contactMethod = document.getElementById("contact_method_list").value;
  const methodList = document.getElementsByClassName("contact__method-choice");
  for (let i = 0; i < methodList.length; i++) {
      methodList[i].classList.add('hidden')
  }
  if (contactMethod === "sms") {
    document.getElementsByClassName("phone")[0].classList.remove('hidden')
  }
  if (contactMethod === "email") {
    document.getElementsByClassName("email")[0].classList.remove('hidden')
  }
  if (contactMethod === "address") {
    document.getElementsByClassName("address")[0].classList.remove('hidden')
  }
}

window.onload = function() {
  showContactMethod()
}
