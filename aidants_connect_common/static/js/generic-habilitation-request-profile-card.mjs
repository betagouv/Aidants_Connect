import {aidantsConnectApplicationReady, BaseController} from "AidantsConnectApplication";

/**
 * @property {String} idValue
 * @property {String} enpointValue
 */
class ProfileEditCard extends BaseController {
    static values = {id: String, enpoint: String}

    buttons = {
        "profile-edit-suppress": {
            classes: "fr-btn--secondary fr-btn--warning fr-btn--icon-left fr-icon-delete-bin-fill",
            content: "Supprimer cet aidant",
            callbackParams: {id: this.idValue},
            callback: this.delete
        },
        "profile-edit-submit": {
            classes: "fr-btn--icon-left fr-icon-pencil-fill",
            content: "Valider les modifications",
            callbackParams: {id: this.idValue},
            callback: this.validate
        }
    }

    initialize () {
        const evtPrefix = this.modalController.identifier
        const evtId = this.modalController.ONCLICK_EVENT
        this.element.setAttribute(
            "data-action",
            `${evtPrefix}:${evtId}@window->${this.identifier}#onBtnClick`
        )
    }

    /**
     * Returns additionnal data to
     * @returns {String|undefined}
     */
    additionnalData () {
        return undefined
    }

    async onEdit () {
        const additionnalData = this.additionnalData()
        const urlParams = additionnalData !== undefined ? `?${additionnalData}` : ""

        this.modalController.showLoader()
        try {
            const response = await fetch(`${this.enpointValue}${urlParams}`)

            if (response.redirected) {
                window.location.replace(response.url)
                return
            }

            this.modalController.show({
                content: await response.text(),
                buttons: {
                    groupClasses: "fr-btns-group--right fr-btns-group--inline-lg fr-btns-group--icon-left",
                    buttons: Object.keys(this.buttons).map(k => Object.assign({id: k}, this.buttons[k]))
                }
            })
        } catch (e) {
            console.error(e)
            return this.modalController.showError()
        }
    }

    onBtnClick ({target, detail: {action, id}}) {
        // Don't act unless modal was created by this instance of ProfileEditCard
        if (`${id}` === this.idValue) {
            this.buttons[action].callback.call(this)
        }
    }

    async validate () {
        const body = new FormData(this.modalController.element.querySelector("form"))
        try {
            const response = await fetch(this.enpointValue, {body, method: "POST"})
            // Error in the form, we return the HTML so that modal can display it
            if (response.status === 422) {
                this.modalController.contentTarget.innerHTML = await response.text()
                return
            }

            // Other error. Modal should display error message
            if (!response.ok) {
                throw response.statusText
            }

            // All is good. Update the <details> and return undefined to let the modal know it shoud close
            this.element.outerHTML = await response.text();
            this.modalController.hide()
        } catch (e) {
            console.error(e)
            return this.modalController.showError()
        }
    }

    /** @returns {Promise} */
    async delete () {
        const form = new FormData(this.modalController.element.querySelector("form"))
        const response = await fetch(this.enpointValue, {
            method: "DELETE",
            headers: {"X-CSRFToken": form.get("csrfmiddlewaretoken")}
        })

        if (response.status === 202) {
            this.element.remove();
            return this.modalController.hide()
        }

        console.error(response.statusText)
        return this.modalController.showError()
    }
}

aidantsConnectApplicationReady.then(app => app.register("profile-edit-card", ProfileEditCard))
