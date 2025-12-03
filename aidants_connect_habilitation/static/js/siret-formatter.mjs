import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

/**
 * Stimulus controller for SIRET number formatting
 * Formats SIRET input with spaces: XXX XXX XXX XXXXX
 */
class SiretFormatter extends BaseController {
  static targets = ["input"];

  connect() {
    this.formatValue();
  }

  onInput(event) {
    this.formatValue();
  }

  onPaste(event) {
    // Allow paste to complete, then format
    setTimeout(() => this.formatValue(), 0);
  }

  formatValue() {
    const input = this.inputTarget;
    const cursorPosition = input.selectionStart;
    const rawValue = input.value.replace(/\s/g, ""); // Remove existing spaces
    const numericValue = rawValue.replace(/\D/g, ""); // Keep only digits

    // Limit to 14 digits
    const limitedValue = numericValue.slice(0, 14);

    // Format with spaces: XXX XXX XXX XXXXX
    let formattedValue = "";
    for (let i = 0; i < limitedValue.length; i++) {
      if (i === 3 || i === 6 || i === 9) {
        formattedValue += " ";
      }
      formattedValue += limitedValue[i];
    }

    // Update input value
    input.value = formattedValue;

    // Restore cursor position, accounting for added spaces
    const newCursorPosition = this.calculateCursorPosition(
      cursorPosition,
      rawValue,
      formattedValue
    );
    input.setSelectionRange(newCursorPosition, newCursorPosition);
  }

  calculateCursorPosition(oldPosition, oldValue, newValue) {
    // Count spaces before the cursor position in the old value
    const spacesBeforeOld = (oldValue.slice(0, oldPosition).match(/\s/g) || [])
      .length;

    // Calculate position in the numeric-only string
    const numericPosition = oldPosition - spacesBeforeOld;

    // Calculate how many spaces should be before this position in the new formatted value
    let spacesBeforeNew = 0;
    if (numericPosition > 3) spacesBeforeNew++;
    if (numericPosition > 6) spacesBeforeNew++;
    if (numericPosition > 9) spacesBeforeNew++;

    return Math.min(numericPosition + spacesBeforeNew, newValue.length);
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("siret-formatter", SiretFormatter)
);
