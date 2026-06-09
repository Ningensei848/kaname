export interface GuardResult {
	ok: boolean;
	errors: string[];
}

export interface VaultDocument {
	path: string;
	title: string;
	markdown: string;
}
