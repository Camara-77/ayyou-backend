import io
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from apps.payments.models import Facture


class InvoicePdfService:
    """
    Service d'impression et de génération de factures au format PDF binaire.
    Utilise ReportLab pour construire un document professionnel et structuré.
    """

    @staticmethod
    def generate_pdf(facture: Facture) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        elements = []

        # Style personnalisé
        primary_color = colors.HexColor('#00875A') # AYYOU Green
        secondary_color = colors.HexColor('#172B4D')
        light_bg = colors.HexColor('#F4F5F7')

        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary_color
        )

        subtitle_style = ParagraphStyle(
            'InvoiceSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.gray
        )

        label_style = ParagraphStyle(
            'InvoiceLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=secondary_color
        )

        body_style = ParagraphStyle(
            'InvoiceBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.black
        )

        # En-tête du document
        header_data = [
            [
                Paragraph("<b>AYYOU PRO</b><br/><font size=9 color='#6B778C'>Plateforme de Livraison & Service Client</font>", title_style),
                Paragraph(f"<b>FACTURE</b><br/><font size=10 color='#00875A'>N° {facture.numero_facture}</font>", ParagraphStyle('RightHeader', parent=title_style, alignment=2))
            ]
        ]
        header_table = Table(header_data, colWidths=[10*cm, 7*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.5*cm))
        elements.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=15))

        # Informations Client & Commande
        date_em = facture.date_emission.strftime('%d/%m/%Y à %H:%M') if facture.date_emission else 'N/A'
        date_pay = facture.date_paiement.strftime('%d/%m/%Y à %H:%M') if facture.date_paiement else 'Non disponible'
        statut_txt = "<font color='#00875A'><b>PAYÉE / ACQUITTÉE</b></font>" if facture.est_payee else "<font color='#DE350B'><b>EN ATTENTE DE PAIEMENT</b></font>"

        meta_data = [
            [
                Paragraph("<b>Informations Client</b>", label_style),
                Paragraph("<b>Détails Règlement</b>", label_style)
            ],
            [
                Paragraph(f"<b>Destinataire:</b> {facture.nom_client_snapshot}<br/>"
                          f"<b>Téléphone:</b> {facture.telephone_client_snapshot}<br/>"
                          f"<b>Adresse:</b> {facture.adresse_livraison_snapshot}", body_style),
                Paragraph(f"<b>Date d'émission:</b> {date_em}<br/>"
                          f"<b>Date de paiement:</b> {date_pay}<br/>"
                          f"<b>Statut:</b> {statut_txt}", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[8.5*cm, 8.5*cm])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), light_bg),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 2),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 0.8*cm))

        # Tableau des articles
        items_data = [
            [Paragraph("<b>Désignation / Article</b>", label_style),
             Paragraph("<b>Qté</b>", ParagraphStyle('C', parent=label_style, alignment=1)),
             Paragraph("<b>Prix unitaire (FCFA)</b>", ParagraphStyle('R', parent=label_style, alignment=2)),
             Paragraph("<b>Total (FCFA)</b>", ParagraphStyle('R', parent=label_style, alignment=2))]
        ]

        details = facture.details_lignes_snapshot or []
        if not details and facture.commande:
            for sc in facture.commande.sous_commandes.all():
                for ligne in sc.lignes.all():
                    details.append({
                        'nom': ligne.plat.nom if ligne.plat else 'Article',
                        'quantite': ligne.quantite,
                        'prix_unitaire': str(ligne.prix_unitaire),
                        'total': str(ligne.quantite * ligne.prix_unitaire)
                    })

        if details:
            for item in details:
                nom = item.get('nom', item.get('libelle', 'Article'))
                qte = item.get('quantite', 1)
                pu = Decimal(str(item.get('prix_unitaire', item.get('prix', 0))))
                tot = Decimal(str(item.get('total', qte * pu)))

                items_data.append([
                    Paragraph(nom, body_style),
                    Paragraph(str(qte), ParagraphStyle('C', parent=body_style, alignment=1)),
                    Paragraph(f"{pu:,.0f}".replace(',', ' '), ParagraphStyle('R', parent=body_style, alignment=2)),
                    Paragraph(f"{tot:,.0f}".replace(',', ' '), ParagraphStyle('R', parent=body_style, alignment=2))
                ])
        else:
            items_data.append([
                Paragraph("Commande de restauration / marchandises", body_style),
                Paragraph("1", ParagraphStyle('C', parent=body_style, alignment=1)),
                Paragraph(f"{facture.montant_ht:,.0f}".replace(',', ' '), ParagraphStyle('R', parent=body_style, alignment=2)),
                Paragraph(f"{facture.montant_ht:,.0f}".replace(',', ' '), ParagraphStyle('R', parent=body_style, alignment=2))
            ])

        items_table = Table(items_data, colWidths=[8*cm, 2*cm, 3.5*cm, 3.5*cm])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DFE1E6')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.5*cm))

        # Récapitulatif Financier
        tot_ht = facture.montant_ht
        frais_liv = facture.frais_livraison
        tot_ttc = facture.montant_total

        summary_data = [
            [Paragraph("Sous-total HT:", label_style), Paragraph(f"{tot_ht:,.0f} FCFA".replace(',', ' '), ParagraphStyle('R', parent=body_style, alignment=2))],
            [Paragraph("Frais de livraison:", label_style), Paragraph(f"{frais_liv:,.0f} FCFA".replace(',', ' '), ParagraphStyle('R', parent=body_style, alignment=2))],
            [Paragraph("<b>TOTAL TTC REGLE:</b>", ParagraphStyle('Tot', parent=label_style, fontSize=11, textColor=primary_color)),
             Paragraph(f"<b>{tot_ttc:,.0f} FCFA</b>".replace(',', ' '), ParagraphStyle('TotVal', parent=body_style, fontSize=11, alignment=2, textColor=primary_color))]
        ]
        summary_table = Table(summary_data, colWidths=[4*cm, 4*cm], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEABOVE', (0,-1), (-1,-1), 1, primary_color),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(summary_table)

        elements.append(Spacer(1, 1.5*cm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceAfter=10))
        elements.append(Paragraph("<font size=8 color='#6B778C'>AYYOU PRO — Service de livraison de restauration et marchandises.<br/>Facture générée automatiquement et délivrée de manière électronique.</font>", ParagraphStyle('Footer', alignment=1)))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    @staticmethod
    def generate_pro_subscription_pdf(facture) -> bytes:
        from apps.payments.models import FactureAbonnement
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        elements = []

        primary_color = colors.HexColor('#00875A')
        secondary_color = colors.HexColor('#172B4D')
        light_bg = colors.HexColor('#F4F5F7')

        title_style = ParagraphStyle(
            'ProInvoiceTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary_color
        )

        label_style = ParagraphStyle(
            'ProInvoiceLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=secondary_color
        )

        body_style = ParagraphStyle(
            'ProInvoiceBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.black
        )

        # Header
        header_data = [
            [
                Paragraph("<b>AYYOU PRO</b><br/><font size=9 color='#6B778C'>Abonnement Partenaire Restaurant / Vendeur</font>", title_style),
                Paragraph(f"<b>FACTURE PRO</b><br/><font size=10 color='#00875A'>N° {facture.numero_facture}</font>", ParagraphStyle('RightHeader', parent=title_style, alignment=2))
            ]
        ]
        header_table = Table(header_data, colWidths=[10*cm, 7*cm])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.5*cm))
        elements.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=15))

        # Metadata
        date_em = facture.date_emission.strftime('%d/%m/%Y à %H:%M') if facture.date_emission else 'N/A'
        date_debut_str = facture.abonnement.date_debut.strftime('%d/%m/%Y') if (facture.abonnement and facture.abonnement.date_debut) else 'N/A'
        date_fin_str = facture.abonnement.date_expiration.strftime('%d/%m/%Y') if (facture.abonnement and facture.abonnement.date_expiration) else 'N/A'

        meta_data = [
            [
                Paragraph("<b>Établissement & Propriétaire</b>", label_style),
                Paragraph("<b>Détails de l'Abonnement</b>", label_style)
            ],
            [
                Paragraph(f"<b>Établissement:</b> {facture.nom_etablissement_snapshot} ({facture.type_etablissement_snapshot})<br/>"
                          f"<b>Propriétaire:</b> {facture.nom_proprietaire_snapshot}<br/>"
                          f"<b>Email:</b> {facture.email_proprietaire_snapshot}", body_style),
                Paragraph(f"<b>Date d'émission:</b> {date_em}<br/>"
                          f"<b>Période de couverture:</b> Du {date_debut_str} au {date_fin_str}<br/>"
                          f"<b>Statut:</b> <font color='#00875A'><b>RÉGLÉ ET ACTIF</b></font>", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[8.5*cm, 8.5*cm])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (-1,-1), light_bg),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 2),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 0.8*cm))

        # Items Table
        items_data = [
            [Paragraph("<b>Désignation du service</b>", label_style),
             Paragraph("<b>Durée</b>", ParagraphStyle('C', parent=label_style, alignment=1)),
             Paragraph("<b>Montant HT</b>", ParagraphStyle('R', parent=label_style, alignment=2)),
             Paragraph("<b>Total (FCFA)</b>", ParagraphStyle('R', parent=label_style, alignment=2))],
            [Paragraph("Abonnement Mensuel PRO AYYOU — Accès Plateforme, Visibilité & Commandes", body_style),
             Paragraph("1 mois", ParagraphStyle('C', parent=body_style, alignment=1)),
             Paragraph("10 000 FCFA", ParagraphStyle('R', parent=body_style, alignment=2)),
             Paragraph("10 000 FCFA", ParagraphStyle('R', parent=body_style, alignment=2))]
        ]
        items_table = Table(items_data, colWidths=[8*cm, 2*cm, 3.5*cm, 3.5*cm])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DFE1E6')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.5*cm))

        # Summary
        summary_data = [
            [Paragraph("<b>TOTAL REGLÉ TTC:</b>", ParagraphStyle('Tot', parent=label_style, fontSize=11, textColor=primary_color)),
             Paragraph("<b>10 000 FCFA</b>", ParagraphStyle('TotVal', parent=body_style, fontSize=11, alignment=2, textColor=primary_color))]
        ]
        summary_table = Table(summary_data, colWidths=[4*cm, 4*cm], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEABOVE', (0,-1), (-1,-1), 1, primary_color),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(summary_table)

        elements.append(Spacer(1, 1.5*cm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceAfter=10))
        elements.append(Paragraph("<font size=8 color='#6B778C'>AYYOU PRO — Facture officielle émise par AYYOU.<br/>Toute contestation doit être adressée au support partenaire dans un délai de 7 jours.</font>", ParagraphStyle('Footer', alignment=1)))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

