import {Controller} from "Stimulus";
import {aidantsConnectApplicationReady, BaseController} from "AidantsConnectApplication";


/**
 * @property {HTMLElement} contentTarget
 * @property {HTMLElement} titleTarget
 * @property {HTMLElement} footerTarget
 * @property {HTMLImageElement} loaderTarget
 * @property {HTMLElement} errorTarget
 * @property {ProfileEditCard[]} profileEditCardOutlets
 * @property {Number} idValue
 * @property {Number} stateValue
 * @property {Boolean} displayValue
 */
class ProfileEditModal extends BaseController {
    static STATES = Object.freeze({
        IDLE: 1,
        LOADING: 2,
        ERROR: 3,
    })

    static outlets = ["profile-edit-card"]
    static targets = ["title", "content", "footer", "loader", "error"]
    static values = {
        id: {type: String, default: undefined},
        state: {type: Number, default: ProfileEditModal.STATES.IDLE},
        display: {type: Boolean, default: false},
    }

    initialize () {
        /** @type {{String: ProfileEditCard}} */
        this.profileEditCards = {}
    }

    stateValueChanged (state) {
        if (state === ProfileEditModal.STATES.LOADING) {
            this.hideElement(this.contentTarget);
            this.hideElement(this.footerTarget);
            this.hideElement(this.errorTarget);
            this.showElement(this.loaderTarget);
        } else if (state === ProfileEditModal.STATES.ERROR) {
            this.hideElement(this.contentTarget);
            this.hideElement(this.footerTarget);
            this.hideElement(this.loaderTarget);
            this.showElement(this.errorTarget);
        } else {
            this.showElement(this.contentTarget);
            this.showElement(this.footerTarget);
            this.hideElement(this.loaderTarget);
            this.hideElement(this.errorTarget);
        }
    }

    displayValueChanged (display) {
        if (display) {
            dsfr(this.element).modal.disclose();
        } else {
            dsfr(this.element).modal.conceal();
        }
    }

    /**@param {ProfileEditCard} outlet  */
    profileEditCardOutletConnected (outlet) {
        this.profileEditCards[outlet.idValue] = outlet
    }

    /**@param {ProfileEditCard} outlet  */
    profileEditCardOutletDisconnected (outlet) {
        delete this.profileEditCards[outlet.idValue]
    }

    /**
     * @param {String} title Modal title
     * @param {String|Promise<String>} content Modal content as HTML string or promise that resolves into HTML string
     * @param {String} id Id of the item being edited
     */
    createAndShow ({title = undefined, content, id} = {}) {
        this.idValue = id
        if (content instanceof Promise) {
            this.stateValue = ProfileEditModal.STATES.LOADING;
        } else {
            content = Promise.resolve(content);
        }

        this.displayValue = true

        content.then(html => {
            this.contentTarget.innerHTML = html;
            this.idValue = id;
            this.stateValue = ProfileEditModal.STATES.IDLE;
        }).catch(() => {
            this.stateValue = ProfileEditModal.STATES.ERROR;
        })
    }

    onDelete (evt) {
        const controller = this.profileEditCards[this.idValue]
        if (controller) {

        }
    }

    onValidate (evt) {
        const controller = this.profileEditCards[this.idValue]
        if (controller) {
            this.stateValue = ProfileEditModal.STATES.LOADING
            controller
                .validate()
                .then(result => {
                    // All is well; empty modal and hide
                    if (result === undefined) {
                        this.contentTarget.innerHTML = "";
                        this.displayValue = false;
                    } else {
                        this.contentTarget.innerHTML = result;
                    }
                })
                .catch(err => {
                    console.error(err)
                    this.stateValue = ProfileEditModal.STATES.ERROR;
                })
                .finally(() => {this.stateValue = ProfileEditModal.STATES.IDLE})
        }
    }

    onConceal (evt) {
        // Reflect changes produced by clicking outside the dialog
        this.displayValue = false;
    }
}

/**
 * @property {String} idValue
 * @property {String} enpointValue
 * @property {ProfileEditModal} profileEditModalOutlet
 */
class ProfileEditCard extends Controller {
    static values = {id: String, enpoint: String}
    static outlets = ["profile-edit-modal"]

    onEdit (elt) {
        this.profileEditModalOutlet.createAndShow({
            id: this.idValue,
            content: fetch(this.enpointValue).then(async response => {
                if (!response.ok) {
                    throw response.statusText
                }
                return await response.text();
            })
        });
    }

    /**
     *
     * @returns {Promise<String|undefined>}
     */
    async validate () {
        return fetch(this.enpointValue, {
            body: new FormData(this.profileEditModalOutlet.contentTarget.querySelector("form")),
            method: "POST",
        }).then(async response => {
            // Error in the form, we return the HTML so that modal can display it
            if (response.status === 422) {
                return await response.text()
            }

            // Other error. Modal should display error message
            if (!response.ok) {
                throw response.statusText
            }

            // All is good. Update the <details> and return undefined to let the modal know it shoud close
            this.element.outerHTML = await response.text();
            return undefined
        })
    }

    async delete () {
    }
}

aidantsConnectApplicationReady.then(/** @param {Stimulus.Application} app */ app => app.register("profile-edit-modal", ProfileEditModal))
aidantsConnectApplicationReady.then(/** @param {Stimulus.Application} app */ app => app.register("profile-edit-card", ProfileEditCard))
