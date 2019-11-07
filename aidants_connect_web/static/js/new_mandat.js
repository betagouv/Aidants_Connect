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
  const suggestions = document.getElementById("address__suggestions")
  const address = document.getElementById("id_contact_address")

  if (contactMethod) {
    showContactMethod(contactMethod)

    contactMethod.addEventListener('change', evt => {
      showContactMethod(contactMethod)
    })
  }

  if (address) {
    address.addEventListener("keyup", evt => {
      if (address.value.length > 5) {
        fetch("https://api-adresse.data.gouv.fr/search/?q="+ evt.target.value +"?autocomplete=1")
        .then(response => response.json())
        .then(data => {

          while (suggestions.firstChild) {
             suggestions.removeChild(suggestions.firstChild);
          }

          data.features.forEach(feature => {
            let el = document.createElement('li')
            el.classList.add('suggestion')
            el.innerHTML = `<strong>${feature.properties.label}</strong><p>${feature.properties.context}</p>`
            suggestions.appendChild(el)
            suggestions.classList.remove('hidden')
          })
        })
      }
    })
  }

  document.addEventListener('click', evt => {
    if (evt.target.classList.contains('suggestion')) {
      address.value = evt.target.firstElementChild.textContent
    }
    suggestions.classList.add('hidden')
  })
}
