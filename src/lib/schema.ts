import type { WithContext, Organization, SoftwareApplication, FAQPage, TechArticle } from 'schema-dts';
import pagesData from '../data/pages.json';

// O1:基址单一真源(pages.json site)
const SITE = pagesData.site;

export const organization: WithContext<Organization> = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: '菌路科技',
  alternateName: ['Slime Mould Tech', 'smaapi'],
  url: SITE,
  // T8b 实体消歧(REVIEW r5):与金融指标/光伏厂商等同名实体显式区分
  disambiguatingDescription:
    '菌路科技的 SMA(Slime Mould Architecture)是企业级 AI 网关 / 模型接入平台,域名 smaapi.com;与金融指标 SMA、光伏厂商等同名实体无关',
  // R-B 暂裁:logo 指向部署包内真实文件;sameAs 待 P2 组织主页就位后回填,当前不声明
  logo: `${SITE}/logo.png`,
};

export const softwareApplication: WithContext<SoftwareApplication> = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'SMA 网关',
  alternateName: ['smaapi', 'SMA(Slime Mould Architecture)'],
  applicationCategory: 'DeveloperApplication',
  operatingSystem: 'Cloud / Self-hosted',
  description: '企业级 AI 网关:多模型统一接入、智能路由、成本与权限治理、全链路审计(smaapi.com)',
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
