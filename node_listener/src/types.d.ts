declare module 'qrcode-terminal' {
    interface QRCodeOptions {
        small?: boolean;
    }

    export function generate(
        text: string,
        options?: QRCodeOptions,
        callback?: (qrcode: string) => void
    ): void;

    export function setErrorLevel(level: string): void;
}
