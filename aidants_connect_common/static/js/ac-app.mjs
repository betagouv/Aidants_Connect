import {Application, Controller} from "Stimulus"


class BaseController extends Controller {
    /** @returns {MainModal} */
    get modalController () {
        if (this._modalController === undefined) {
            this._modalController = this.application.getControllerForElementAndIdentifier(
                document.querySelector('[data-controller="main-modal"]'), "main-modal"
            )
        }
        return this._modalController
    }

    noop () { /* Does nothing */ }

    showElement (elt) {
        elt.removeAttribute("hidden");
        elt.removeAttribute("aria-hidden");
    }

    hideElement (elt) {
        elt.setAttribute("hidden", "hidden");
        elt.setAttribute("aria-hidden", "true");
    }

    mutateVisibility (visibility, elt) {
        if (visibility) this.showElement(elt);
        else this.hideElement(elt);
    }

    mutateRequirement (required, elt) {
        if (required) elt.setAttribute("required", "required");
        else elt.removeAttribute("required");
    }
}

/**
 * @typedef {Object} ButtonDefinition
 * @property {String} [classes]
 * @property {String} id
 * @property {String} content
 * @property {Object<String, String>} [callbackParams]
 */
/**
 * @typedef {Object} ButtonGroupDefinition
 * @property {String} [groupClasses]
 * @property {ButtonDefinition[]} buttons
 */
/**
 * @property {String} titleValue
 * @property {String} stateValue
 *
 * @property {HTMLElement} dialogTarget
 * @property {HTMLElement} titleTarget
 * @property {HTMLElement} contentTarget
 * @property {HTMLElement} footerTarget
 * @property {HTMLTemplateElement} loaderTplTarget
 * @property {HTMLTemplateElement} errorTplTarget
 * @property {HTMLButtonElement} footerButtonTargets
 */
class MainModal extends BaseController {
    static ONCLICK_EVENT = "onClick"
    static STATES = Object.freeze({
        HIDDEN: 0,
        VISIBLE: 1
    })
    static targets = ["dialog", "title", "content", "footer", "loaderTpl", "errorTpl", "footerButton"]
    static values = {
        title: {type: String, default: ""},
        footer: {type: Object, default: undefined},
        state: {type: Number, default: MainModal.STATES.HIDDEN}
    }

    get ONCLICK_EVENT() {
        return this.constructor.ONCLICK_EVENT
    }
    get STATES () {
        return this.constructor.STATES
    }

    /**
     *
     * @param {String} [title] Modal title
     * @param {String} content Modal body. Must be valid HTML
     * @param {ButtonGroupDefinition} [buttons]
     */
    show ({title = "", content, buttons = undefined}) {
        this.titleValue = title
        this.contentTarget.innerHTML = content
        this.__setFooter(buttons)
        this.stateValue = this.STATES.VISIBLE
    }

    showLoader() {
        this.show({content: this.loaderTplTarget.innerHTML})
    }

    showError() {
        this.show({content: this.errorTplTarget.innerHTML})
    }

    hide () {
        this.stateValue = MainModal.STATES.HIDDEN
    }

    /**
     * @private
     * @param {Number} value New value
     */
    stateValueChanged (value) {
        if (value === this.STATES.VISIBLE) {
            this.showElement(this.element)
            dsfr(this.dialogTarget).modal.disclose()
        } else {
            dsfr(this.dialogTarget).modal.conceal()
            this.contentTarget.innerHTML = ""
            this.titleValue = ""
            this.__setFooter(undefined)
            this.hideElement(this.element)
        }
    }

    /**
     * @private
     * @param {String} value New modal title
     */
    titleValueChanged (value) {
        if (value.length === 0) {
            this.titleTarget.textContent = ""
            this.hideElement(this.titleTarget)
        } else {

            this.titleTarget.textContent = `${value}`
            this.showElement(this.titleTarget)
        }
    }

    /** @private */
    onClick ({target, params}) {
        this.dispatch(this.ONCLICK_EVENT, {detail: params})
    }

    /** @private */
    onConceal () {
        this.stateValue = this.STATES.HIDDEN
    }

    /**
     * @private
     * @param {ButtonDefinition} button
     */
    __createButton (button) {
        button.classes = button.classes ? ` ${button.classes}` : ""
        const params = Object
            .entries(Object.assign({}, button.callbackParams, {action: button.id}))
            .map(([k, v]) => `data-${this.identifier}-${k}-param="${v}"`)
            .join("\n")

        return `<button
            id="${button.id}"
            class="fr-btn${button.classes}"
            data-action="${this.identifier}#onClick:stop:prevent"
            ${params}
            data-${this.identifier}-target="footerButton"
        >${button.content}</button>`
    }

    /**
     * @private
     * @param {ButtonGroupDefinition} [value] New footer buttons
     */
    __setFooter (value) {
        if (value === undefined) {
            this.footerTarget.textContent = ""
            return this.hideElement(this.footerTarget)
        }

        value.groupClasses = value.groupClasses ? ` ${value.groupClasses}` : ""
        this.footerTarget.innerHTML = `<div class="fr-btns-group${value.groupClasses}">
            ${value.buttons.map(this.__createButton.bind(this)).join("\n")}
        </div>`
        this.showElement(this.footerTarget)
    }
}

const AidantsConnectApplication = new Application();
/** @type {Promise<Application>} */
const aidantsConnectApplicationReady = Promise.all([AidantsConnectApplication.start(), window.dsfrReady]).then(() => {
    AidantsConnectApplication.register("main-modal", MainModal)
    document.documentElement.dataset.appReady = "true"
    return AidantsConnectApplication
})
export {AidantsConnectApplication, aidantsConnectApplicationReady, BaseController, MainModal}
