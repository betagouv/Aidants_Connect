function showContactMethod(method) {
  const contactValue = method.value
  const methodList = document.getElementsByClassName("contact__method-choice");
  for (let i = 0; i < methodList.length; i++) {
      methodList[i].classList.add('hidden')
  }
  if (contactValue === "sms" || contactValue === "phone") {
    document.getElementsByClassName("phone")[0].classList.remove('hidden')
  }
  if (contactValue === "email") {
    document.getElementsByClassName("email")[0].classList.remove('hidden')
  }
  if (contactValue === "address") {
    document.getElementsByClassName("address")[0].classList.remove('hidden')
  }
}

window.onload = function() {
  const contactMethod = document.getElementById("id_preferred_contact_method")
  if (contactMethod) {
    showContactMethod(contactMethod)
  }

  contactMethod.addEventListener('change', (event) => {
    showContactMethod(contactMethod)
  })
}
