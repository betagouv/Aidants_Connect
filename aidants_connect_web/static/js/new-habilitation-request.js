"use strict";

import {BaseController} from "./base-controller.js"


/**
 * @property {HTMLFormElement} formTarget
 * @property {HTMLElement} leftFormReplaceTarget
 * @property {HTMLElement} partialSubmitBtnTarget
 * @property {HTMLElement} rightFormsSectionTarget
 * @property {HTMLElement} rightFormsInsertTarget
 * @property {HTMLElement} formTplTarget
 * @property {NodeList} editBtnTargets
 * @property {HTMLElement} confirmationDialogTarget
 * @property {NodeList} confirmationDialogTargets
 * @property {HTMLElement} dialogConfirmButtonTarget
 * @property {HTMLElement} dialogCancelButtonTarget
 *
 * @property {String} loadingClass
 * @property {String} editIdleClass
 * @property {String} submitBtnEditClass
 * @property {String} submitBtnValidateClass
 *
 * @property {Number} nbFormCountValue
 * @property {Boolean} loadingValue
 * @property {Number} leftFormIdxValue
 * @property {Boolean} modalOpenedValue
 * @property {Boolean} editingValue
 * @property {String} submitBtnValidateTxtValue
 * @property {String} submitBtnEditTxtValue
 */
class NewHabilitationRequest extends BaseController {
    initialize() {
        this.nbFormCountValue = Number.parseInt(this.mgmtNbFormsInput.value);
        if (this.formTarget.querySelectorAll('input[name*="__prefix__"]').length > 0) {
            this.validateAndResetLeftForm();
        }
    }

    get mgmtNbFormsInput() {
        return document.querySelector('[name$="TOTAL_FORMS"]');
    }

    get leftFormChanged() {
        const form = new FormData(this.formTarget);

        const emptyForm = document.createElement("form");
        emptyForm.replaceChildren(this.leftFormReplaceTarget.cloneNode(true));
        HTMLFormElement.prototype.reset.call(emptyForm);
        // Caching an empty form to compute if form has changed.
        const emptyFormData = new FormData(emptyForm);

        for (const [k, v] of emptyFormData.entries()) {
            if (form.get(k) !== v) {
                return true;
            }
        }

        return false;
    }

    nbFormCountValueChanged(value) {
        this.mgmtNbFormsInput.value = `${value}`;
        value > 1 ? this.showElement(this.rightFormsSectionTarget) : this.hideElement(this.rightFormsSectionTarget);
    }

    modalOpenedValueChanged(value) {
        this.confirmationDialogTargets.forEach(it => {
            if (value) {
                dsfr(it).modal.disclose();
            } else {
                dsfr(it).modal.conceal();
            }
        });
    }

    editingValueChanged(value) {
        if (value) {
            this.partialSubmitBtnTarget.textContent = this.submitBtnEditTxtValue;
            this.partialSubmitBtnTarget.classList.remove(this.submitBtnValidateClass);
            this.partialSubmitBtnTarget.classList.add(this.submitBtnEditClass);
        } else {
            this.partialSubmitBtnTarget.textContent = this.submitBtnValidateTxtValue;
            this.partialSubmitBtnTarget.classList.remove(this.submitBtnEditClass);
            this.partialSubmitBtnTarget.classList.add(this.submitBtnValidateClass);
        }
    }

    loadingValueChanged(value) {
        if (value) {
            this.partialSubmitBtnTarget.classList.forEach(it => {
                if (it.startsWith("fr-icon-")) {
                    this.partialSubmitBtnTarget.classList.remove(it);
                }
            });
            this.partialSubmitBtnTarget.classList.add(this.loadingClass);
            this.partialSubmitBtnTarget.setAttribute("disabled", "disabled");
            this.editBtnTargets.forEach(it => {
                it.classList.remove(this.editIdleClass);
                it.classList.add(this.loadingClass);
                it.setAttribute("disabled", "disabled");
            });
        } else {
            this.partialSubmitBtnTarget.classList.remove(this.loadingClass);
            this.editingValueChanged(this.editingValue);
            this.partialSubmitBtnTarget.removeAttribute("disabled");
            this.editBtnTargets.forEach(it => {
                it.classList.remove(this.loadingClass);
                it.classList.add(this.editIdleClass);
                it.removeAttribute("disabled");
            });
        }
    }

    onPartialSubmit() {
        if (this.loadingValue || !this.formTarget.reportValidity()) {
            return;
        }

        this.loadingValue = true;
        const url = this.editingValue
                    ? Urls.espaceResponsableAidantNewJsEdit({form_idx: this.leftFormIdxValue})
                    : Urls.espaceResponsableAidantNewJs();
        fetch(
            url,
            {method: "POST", body: new FormData(this.formTarget)}
        ).then(async response => {
            if (response.status === 200) {  // Form has an error
                this.leftFormReplaceTarget.innerHTML = await response.text();
            } else if (response.status === 201) {  // Form is ok
                this.rightFormsInsertTarget.insertAdjacentHTML("beforeend", await response.text());
                this.validateAndResetLeftForm();
            }
        }).finally(() => {
            this.loadingValue = false;
        });
    }

    onEdit(evt) {
        if (this.loadingValue) {
            return;
        }

        const formIdx = Number.parseInt(evt.target.dataset.formIdx);
        if (!Number.isInteger(formIdx)) {
            return;
        }

        if (this.leftFormChanged) {
            this.openDialog({onConfirm: () => this.editForm(formIdx)});
            return;
        }

        this.editForm(formIdx);
    }

    /**
     *
     * @param onCancel {function(evt: Event):any | undefined}
     * @param onConfirm {function(evt: Event):any | undefined}
     */
    openDialog({onCancel = undefined, onConfirm = undefined} = {}) {
        const cancelCb = evt => {
            evt.preventDefault();
            evt.stopPropagation();
            this.dialogCancelButtonTarget.removeEventListener("click", cancelCb);
            if (onCancel instanceof Function) {
                onCancel(evt);
            }
            this.modalOpenedValue = false;
        };
        this.dialogCancelButtonTarget.addEventListener("click", cancelCb);

        const confirmCB = evt => {
            evt.preventDefault();
            evt.stopPropagation();
            this.dialogConfirmButtonTarget.removeEventListener("click", confirmCB);
            if (onConfirm instanceof Function) {
                onConfirm(evt);
            }
            this.modalOpenedValue = false;
        };
        this.dialogConfirmButtonTarget.addEventListener("click", confirmCB);

        this.modalOpenedValue = true;
    }

    editForm(formIdx) {
        this.loadingValue = true;
        // We're editing here, so we don't want the empty form to be taken in account during validation
        this.nbFormCountValue = this.nbFormCountValue - 1;
        this.leftFormIdxValue = formIdx;
        this.editingValue = true;
        fetch(
            Urls.espaceResponsableAidantNewJsEdit({form_idx: formIdx}),
            {method: "POST", body: new FormData(this.formTarget)}
        ).then(async response => {
            this.rightFormsInsertTarget.querySelectorAll(
                `[data-${this.identifier}-target="addedForm${formIdx}Container"]`
            ).forEach(it => it.remove());
            this.leftFormReplaceTarget.innerHTML = await response.text();
        }).finally(() => {
            this.loadingValue = false;
        });
    }

    validateAndResetLeftForm() {
        this.leftFormReplaceTarget.innerHTML = this.formTplTarget.innerHTML.replace(
            /__prefix__/g, `${this.nbFormCountValue}`
        );
        this.leftFormIdxValue = this.nbFormCountValue;
        this.nbFormCountValue = this.nbFormCountValue + 1;
        this.editingValue = false;
    }

    static targets = [
        "form",
        "leftFormReplace",
        "partialSubmitBtn",
        "rightFormsSection",
        "rightFormsInsert",
        "formTpl",
        "editBtn",
        "confirmationDialog",
        "dialogConfirmButton",
        "dialogCancelButton",
    ]
    static values = {
        nbFormCount: {type: Number, default: 0},
        loading: {type: Boolean, default: false},
        leftFormIdx: {type: Number, default: 0},
        modalOpened: {type: Boolean, default: false},
        editing: {type: Boolean, default: false},
        submitBtnValidateTxt: String,
        submitBtnEditTxt: String,
    }
    static classes = ["loading", "editIdle", "submitBtnEdit", "submitBtnValidate"]
}

new Promise(resolve => window.addEventListener("load", resolve)).then(() => {
    const application = Stimulus.Application.start();
    application.register("new-habilitation-request", NewHabilitationRequest);
});
