window.onload = function(e) {
  const button = document.querySelector('.show-contact')
  button.addEventListener('click', function (event) {
    const link = event.currentTarget
  	if (link) {
      link.classList.add('hidden')
    	link.nextSibling.classList.remove('hidden')
    }
  }, false)
}
