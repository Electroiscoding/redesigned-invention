export class ApiVaultClient {
  // Secure sessionStorage proxy token handler stub
  public getToken(): string | null {
    return sessionStorage.getItem('proxy-token');
  }
}