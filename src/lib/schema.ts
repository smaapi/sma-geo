import type { WithContext, Organization, SoftwareApplication, FAQPage, TechArticle } from 'schema-dts';

export const organization: WithContext<Organization> = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: '菌路科技',
  alternateName: 'Slime Mould Tech',
  url: 'https://www.smaapi.com',
  // R-B 暂裁:logo 指向部署包内真实文件;sameAs 待 P2 组织主页就位后回填,当前不声明
  logo: 'https://www.smaapi.com/logo.png',
};

export const softwareApplication: WithContext<SoftwareApplication> = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'SMA',
  applicationCategory: 'DeveloperApplication',
  operatingSystem: 'Cloud / Self-hosted',
  description: '企业级 AI 网关:多模型统一接入、智能路由、成本与权限治理、全链路审计',
};

export interface QA {
  q: string;
  a: string;
}

export function faqPage(qa: ReadonlyArray<QA>): WithContext<FAQPage> {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: qa.map(({ q, a }) => ({
      '@type': 'Question',
      name: q,
      acceptedAnswer: { '@type': 'Answer', text: a },
    })),
  };
}

export function techArticle(opts: {
  headline: string;
  description: string;
  url: string;
  inLanguage: string;
  datePublished: string;
  dateModified: string;
}): WithContext<TechArticle> {
  return {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: opts.headline,
    description: opts.description,
    url: opts.url,
    inLanguage: opts.inLanguage,
    datePublished: opts.datePublished,
    dateModified: opts.dateModified,
    author: { '@type': 'Organization', name: '菌路科技' },
  };
}
