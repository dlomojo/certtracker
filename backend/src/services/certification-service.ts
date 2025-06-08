// ============ API SERVICE LAYER ============

import { CertificationRepository } from '../repository/certification-repository';

export class CertificationService {
  private repository: CertificationRepository;
  
  constructor() {
    this.repository = new CertificationRepository();
  }

  async getDashboardData(userId: string) {
    try {
      const certifications = await this.repository.getUserCertifications(userId);
      
      const today = new Date();
      const in30Days = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
      const in60Days = new Date(today.getTime() + 60 * 24 * 60 * 60 * 1000);
      const in90Days = new Date(today.getTime() + 90 * 24 * 60 * 60 * 1000);
      
      const stats = {
        totalCertifications: certifications.length,
        activeCertifications: certifications.filter(c => c.Status === 'active').length,
        expiringIn30Days: certifications.filter(c => {
          const expDate = new Date(c.ExpirationDate);
          return expDate <= in30Days && expDate > today && c.Status === 'active';
        }).length,
        expiringIn60Days: certifications.filter(c => {
          const expDate = new Date(c.ExpirationDate);
          return expDate <= in60Days && expDate > in30Days && c.Status === 'active';
        }).length,
        expiringIn90Days: certifications.filter(c => {
          const expDate = new Date(c.ExpirationDate);
          return expDate <= in90Days && expDate > in60Days && c.Status === 'active';
        }).length,
        expiredCertifications: certifications.filter(c => c.Status === 'expired').length,
        renewedThisYear: certifications.filter(c => {
          const issueDate = new Date(c.IssueDate);
          return issueDate.getFullYear() === today.getFullYear() && c.Status === 'renewed';
        }).length,
        totalCost: certifications.reduce((sum, c) => sum + (c.Cost || 0), 0),
        upcomingRenewalCost: certifications
          .filter(c => new Date(c.ExpirationDate) <= in90Days && c.Status === 'active')
          .reduce((sum, c) => sum + (c.Cost || 0), 0),
        averageCertificationValue: certifications.length > 0 
          ? certifications.reduce((sum, c) => sum + (c.Cost || 0), 0) / certifications.length 
          : 0,
        categoriesCount: {},
        providersCount: {},
        expirationTrend: []
      };
      
      // Count by categories and providers
      certifications.forEach(cert => {
        stats.categoriesCount[cert.Category] = (stats.categoriesCount[cert.Category] || 0) + 1;
        stats.providersCount[cert.Provider] = (stats.providersCount[cert.Provider] || 0) + 1;
      });
      
      return {
        certifications,
        dashboardStats: stats
      };
    } catch (error) {
      console.error('Error getting dashboard data:', error);
      throw error;
    }
  }

  async createCertification(userId: string, certificationData: any) {
    try {
      await this.repository.createCertification(userId, certificationData);
      await this.repository.updateAnalytics(userId);
      return { success: true };
    } catch (error) {
      console.error('Error creating certification:', error);
      throw error;
    }
  }

  async updateCertification(userId: string, certId: string, updates: any) {
    try {
      await this.repository.updateCertification(userId, certId, updates);
      await this.repository.updateAnalytics(userId);
      return { success: true };
    } catch (error) {
      console.error('Error updating certification:', error);
      throw error;
    }
  }

  async deleteCertification(userId: string, certId: string) {
    try {
      await this.repository.deleteCertification(userId, certId);
      await this.repository.updateAnalytics(userId);
      return { success: true };
    } catch (error) {
      console.error('Error deleting certification:', error);
      throw error;
    }
  }
}